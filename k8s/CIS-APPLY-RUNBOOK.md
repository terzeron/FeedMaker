# CIS 하드닝 실행 런북 (2026-10-22 점검 기준)

`cis-hardening-apply.sh`와 `CIS-HARDENING-PLAN.md`의 남은 항목을 **어떤 순서로, 어떤 확인을 하며** 적용할지 정리한다.
모든 단계는 `sudo`가 필요하다. 미리보기는 sudo 없이 `DRY_RUN=1 bash k8s/cis-hardening-apply.sh`로 한다.

## 요약

| 단계 | 항목                                  | 명령                                                                                         | 중단        | 위험      | 선행 조건                  |
| ---- | ------------------------------------- | -------------------------------------------------------------------------------------------- | ----------- | --------- | -------------------------- |
| 0    | 미리보기                              | `DRY_RUN=1 bash k8s/cis-hardening-apply.sh`                                                  | 없음        | 없음      | —                          |
| 1    | CP-4 감사 로그 + CP-5 NodeRestriction | `sudo bash k8s/cis-hardening-apply.sh`                                                       | API 약 20초 | 낮음      | 0단계                      |
| 관찰 | 감사 로그로 익명 접근 사용처 확인     | (아래 쿼리)                                                                                  | —           | —         | 1단계 후 최소 24시간       |
| 2    | CP-3 kubelet Webhook 인가             | `sudo APPLY_AUDIT=0 APPLY_ADMISSION=0 APPLY_KUBELET_AUTHZ=1 bash k8s/cis-hardening-apply.sh` | API 약 20초 | 중간      | 1단계 안정                 |
| 3    | CP-2 apiserver 익명 접근 차단         | `sudo APPLY_AUDIT=0 APPLY_ADMISSION=0 APPLY_ANON=1 bash k8s/cis-hardening-apply.sh`          | API 약 20초 | 낮음~중간 | 관찰 결과 익명 사용처 없음 |
| —    | CP-7 protect-kernel-defaults          | **적용하지 않는다**                                                                          | —           | 충돌      | 아래 "CP-7 결정"           |
| —    | CP-1 RBAC, CP-6 cipher                | 이미 적용됨                                                                                  | —           | —         | —                          |

재기동은 `systemctl restart snap.microk8s.daemon-kubelite`이고 containerd는 건드리지 않는다. 컨테이너는 계속 실행되고 API만 20초쯤 끊길 것으로 예상한다.
(RBAC를 켤 때 같은 방식으로 재시작했고 재시작 직후 비정상 Pod가 없었다. 다만 컨테이너 시작 시각을 비교해 확인하지는 않았다. 1단계 때 `kubectl get pods -A`의 RESTARTS 열이 늘지 않는지 보면 확인된다.)

## 왜 이 순서인가

1. **감사 로그를 먼저 켠다.** 2·3단계(kubelet 인가, 익명 차단)가 무엇을 깨뜨릴지 사전에 알 수 없다. 로그가 있으면 `system:anonymous`를 누가 쓰는지 데이터로 확인한 뒤 끌 수 있다.
   감사 로그는 켜는 것 자체의 위험이 가장 낮다(기록만 추가). NodeRestriction도 같은 apiserver 재시작에 묶어 재시작 횟수를 줄인다.
2. **kubelet 인가(CP-3)를 익명 차단(CP-2)보다 먼저 한다.** CP-3은 바뀌는 경로(apiserver→kubelet, 토큰 클라이언트)가 한정적이고 아래 사전 검증이 끝나 있다. 실패해도 증상이 즉시 보인다(`kubectl logs/top`).
3. **익명 차단(CP-2)은 관찰 후에 한다.** 익명 `/readyz`는 지금 200이다(RBAC의 `system:public-info-viewer`). 끄면 401이 된다. microk8s 내부 스크립트는 클라이언트 인증서로 호출하므로 안전하지만, 외부 모니터링 등이 있을 수 있다.
4. **단계마다 재시작을 따로 한다.** 실패했을 때 어느 플래그 때문인지 바로 알 수 있고 롤백 범위가 한 파일로 좁혀진다.

## 사전 점검 결과 (모두 실측)

- apiserver→kubelet 클라이언트 인증서: `CN=kube-apiserver-kubelet-client, O=system:masters` → Webhook 인가에서도 항상 허용.
- kubelet 자신의 신원: `CN=system:node:yicho-ser7, O=system:nodes` → Node 인가와 NodeRestriction이 맞는 신원. `system:node:yicho-ser7`가 `subjectaccessreviews`와 `tokenreviews`를 만들 수 있음(kubelet Webhook에 필요).
- kubelet 현재: `--anonymous-auth=false`, `--authentication-token-webhook=true`, `--read-only-port=0`. **`--authorization-mode`는 없어서(기본 AlwaysAllow) 인증만 통과하면 kubelet API가 열려 있다.** CP-3이 이를 막는다.
- kubelet API 소비자의 RBAC: Prometheus와 metrics-server SA 모두 `nodes/metrics`, `nodes/stats`, `nodes/proxy`, `nodes/log` get 허용.
- apiserver 익명 접근: 지금 `/readyz` 200, `/api` 403. 클러스터 안에서 apiserver를 프로브로 직접 치는 Pod는 없음. microk8s 내부의 `/readyz` 호출은 클라이언트 인증서(`utils.sh`)를 쓴다.
- 현재 apiserver `--enable-admission-plugins=EventRateLimit`만 있어 NodeRestriction이 빠져 있음(기본 활성 목록에 없다).

## 발견한 스크립트 결함 (이번에 고침)

| 결함                                                   | 영향                                                                                                                         | 수정                                                                                                                                                     |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `microk8s stop; microk8s start`로 재기동               | **containerd까지 멈춰 모든 컨테이너가 재시작**(DB 복구, 서비스 중단 수 분)                                                   | `systemctl restart snap.microk8s.daemon-kubelite`                                                                                                        |
| `APPLY_RBAC=1`이 CP-1(`microk8s enable rbac`)을 재실행 | 이미 켜진 RBAC를 다시 건드림. 또 `enable`은 인자만 바꾸고 apiserver를 재시작하지 못한다(이번에 겪음)                         | 이미 RBAC면 건너뜀, CP-3은 별도 플래그 `APPLY_KUBELET_AUTHZ`                                                                                             |
| NodeRestriction 단계가 없음(계획서 CP-5-2에는 있음)    | 적용되지 않은 채 남음                                                                                                        | `add_admission_plugin`으로 기존 값을 보존해 추가                                                                                                         |
| 익명 차단 검증이 `can-i --as=system:anonymous`         | 플래그와 무관하게 항상 `no` → 검증이 되지 않음                                                                               | 익명 `curl /readyz`가 401인지 확인                                                                                                                       |
| 재기동 후 API가 안 뜨면 수동 복구                      | 잘못된 정책 하나로 apiserver가 못 뜨면 `kubectl`도 안 된다                                                                   | 180초 안에 안 뜨면 백업 복원 후 재기동(자동)                                                                                                             |
| 감사 정책이 잡음                                       | 쓰기 요청의 59%가 leases, 13%가 endpoints → 하루 약 34만 건/170MB, `maxsize 100 x maxbackup 10`이면 보존 약 6일(의도는 30일) | `audit-policy.yaml`에 None 규칙 추가(leases, endpoints, events, status 갱신, tokenreviews, subjectaccessreviews, 헬스체크). 약 85% 제외 → 30일 보존 가능 |
| `APPLY_BASELINE`이 CP-2까지 묶음                       | 감사 확인 전에 익명이 꺼진다                                                                                                 | CP-2는 `APPLY_ANON`으로 분리(기본 OFF)                                                                                                                   |

## 단계별 절차

### 0단계 — 미리보기 (sudo 불필요)

```bash
cd ~/workspace/fm_dev
DRY_RUN=1 bash k8s/cis-hardening-apply.sh
```

변경될 줄이 `기존값 -> 새값`으로 나온다. `audit-policy.yaml` 문법 검사도 이때 한다.

### 1단계 — 감사 로그 + NodeRestriction

```bash
sudo bash k8s/cis-hardening-apply.sh
```

확인(스크립트가 자동 출력 + 아래):

```bash
sudo ls -l /var/log/apiserver/audit.log          # 커지고 있어야 한다
kubectl get pods -A --no-headers | grep -vE 'Running|Completed'   # 없어야 한다
kubectl get --raw /readyz
```

롤백: `sudo cp -a /var/snap/microk8s/current/args/kube-apiserver.bak.<타임스탬프> /var/snap/microk8s/current/args/kube-apiserver && sudo systemctl restart snap.microk8s.daemon-kubelite`
(스크립트는 API가 180초 안에 안 뜨면 이를 자동으로 한다.)

일일 점검: 로그 용량이 예상(약 20~30MB/일)인지 본다. 크면 `audit-policy.yaml`에 None 규칙을 더 추가한다.

### 관찰 — 익명 접근 사용처 (1단계 후 최소 24시간)

크론 주기가 하루 단위이므로 24시간 이상 본다.

```bash
sudo python3 - <<'EOF'
import json,collections
c=collections.Counter()
for l in open("/var/log/apiserver/audit.log"):
    try: e=json.loads(l)
    except: continue
    if e.get("user",{}).get("username")=="system:anonymous" or "system:unauthenticated" in e.get("user",{}).get("groups",[]):
        c[(e.get("requestURI","")[:60], (e.get("sourceIPs") or [""])[0], e.get("userAgent","")[:40])]+=1
for k,v in c.most_common(20): print(v,k)
print("항목 수:",len(c))
EOF
```

- 항목이 없거나 `192.168.x.x`에서 직접 친 확인용 `curl` 뿐이면 3단계로 간다.
- 정상 사용처가 있으면(예: 외부 헬스체크) 그 클라이언트를 인증된 방식으로 바꾼 뒤에 3단계로 간다.

### 2단계 — kubelet Webhook 인가 (CP-3)

```bash
sudo APPLY_AUDIT=0 APPLY_ADMISSION=0 APPLY_KUBELET_AUTHZ=1 bash k8s/cis-hardening-apply.sh
```

스크립트가 `kubectl logs`와 `kubectl top nodes`를 확인한다. 추가 확인:

```bash
kubectl exec -n wiki deploy/sw-wiki -- true                       # apiserver -> kubelet exec
kubectl port-forward -n observability svc/kube-prom-stack-kube-prome-prometheus 19090:9090 &
curl -s 'http://127.0.0.1:19090/api/v1/targets?state=active' | python3 -c "import json,sys,collections;print(collections.Counter(t['health'] for t in json.load(sys.stdin)['data']['activeTargets']))"   # 전부 up (kubelet 3개 포함)
```

실패 징후: `kubectl logs/exec`가 403, `kubectl top`이 `metrics not available`, Prometheus의 `kubelet` 타깃이 down.
롤백: `kubelet.bak.<타임스탬프>` 복원 후 kubelite 재시작.

**2단계 실행 결과 (2026-10-23)**: 적용 성공. `kubectl logs/exec` 정상, Prometheus kubelet 타깃 3개 up, 비정상 Pod 없음. 스크립트의 `kubectl top` 검증이 한 번 실패로 나왔으나 kubelet 재기동 직후 metrics-server의 첫 수집이 `connection refused`였던 일시 현상이었다(곧 정상, APIService Available). 이 일시 실패 때문에 검증을 90초 재시도로 고쳤다. Webhook이 실제로 집행되는지도 확인했다: 권한 없는 SA(`wiki/default`) 토큰으로 kubelet `/pods`·`/metrics` → **403**, Prometheus SA 토큰 `/metrics` → 200, 익명 `/pods` → 401(이전 AlwaysAllow에서는 인증만 되면 열려 있었다).

### 3단계 — 익명 접근 차단 (CP-2)

```bash
sudo APPLY_AUDIT=0 APPLY_ADMISSION=0 APPLY_ANON=1 bash k8s/cis-hardening-apply.sh
```

스크립트가 익명 `/readyz`가 **401**인지 확인한다. 추가 확인: 외부 호스트 응답, `kubectl get nodes`, `microk8s status`.
롤백: `kube-apiserver.bak.<타임스탬프>` 복원 후 kubelite 재시작.

**3단계 실행 결과 (2026-10-23)**: 적용 성공. 익명 `/readyz`, `/healthz`, `/livez`, `/version`, `/api`가 모두 401. 인증된 접근(관리자 `kubectl`)은 그대로이고, 클러스터 구성요소 로그(kube-system, metallb-system, cert-manager, traefik, textmanager, observability, automation, blog, wiki, feedmaker)에서 최근 5분간 Unauthorized 0건, `kubectl top` 정상, Prometheus 타깃 15개 up, 인증서 11개 Ready, 외부 호스트 10개 정상, 비정상 Pod 없음. 이로써 계획 항목 중 CP-1~CP-6과 NodeRestriction이 모두 적용됐다. 남은 것은 CP-7(아래 결정 사항)과 H-1(범위 밖)이다.

## CP-7 결정 — 적용하지 않는다 (사용자 판단 필요)

`--protect-kernel-defaults=true`는 kubelet이 요구하는 커널 값과 실제 값이 **다르면 kubelet이 기동하지 못하게** 한다. 요구값 6개 중 5개는 이미 같지만 `vm.overcommit_memory`가 문제다.

- kubelet이 요구하는 값: `vm.overcommit_memory=1`.
- 사용자의 `/etc/sysctl.d/99-oom-hardening.conf`: **`vm.overcommit_memory = 0`** (2026-08-04 OOM 폭주 대응. 1이면 폭주 프로세스가 RAM+swap을 전부 받아가 커널이 파드를 학살한다는 사유).
- **실제 현재 값: 1.** 영구 설정은 0인데 실행 중 값이 1이다. kubelet이 `--protect-kernel-defaults`를 쓰지 않을 때 시작하면서 이 값을 덮어쓰는 동작과 일치한다(추론이며 아래 진단으로 확인한다). 오늘 kubelet을 여러 번 재시작했다.

따라서:

- CP-7을 켜면: (재부팅 후) 설정 파일의 0 때문에 kubelet이 기동하지 못하거나, 값을 1로 맞추면 OOM 대응 설정을 포기하게 된다.
- 지금 상태 그대로: **8월 OOM 대응 설정이 사실상 적용되지 않고 있다.** CIS와 별개로 확인할 가치가 있다.

진단(약 20초 API 중단, 파드 재시작 없음):

```bash
sudo sysctl -w vm.overcommit_memory=0
sudo systemctl restart snap.microk8s.daemon-kubelite
sleep 30; sysctl vm.overcommit_memory      # 1 이면 kubelet이 덮어쓴 것
```

**진단 결과 (2026-10-23, 사용자 실행)**: `sysctl -w vm.overcommit_memory=0` 후 kubelite를 재시작하자 값이 **1로 되돌아갔다.** kubelet이 시작할 때마다 덮어쓴다는 것이 확정됐다. 따라서 `99-oom-hardening.conf`(0)는 부팅 때 적용돼도 kubelet 시작 직후 1이 되어 **한 번도 실제로 적용된 적이 없다.**

같은 시점의 호스트 상태:
- RAM 27GiB(가용 10GiB), **스왑 8GiB 중 거의 전부 사용(여유 5.6MB)**. 스왑 상위는 node 874MB, 호스트 docker의 elasticsearch-nori(java) 616MB.
- 메모리 limit이 없는 컨테이너 31개. QoS는 BestEffort 18 / Burstable 24 / Guaranteed 5. BestEffort에 **Traefik, Prometheus(실사용 약 982Mi), Grafana, Calico controllers, MetalLB, hostpath-provisioner**가 있다(OOM 시 가장 먼저 죽는 후보, oom_score_adj 1000).
- Burstable도 request가 작으면 adj가 999에 가까워 실질적 보호는 Guaranteed(request=limit, adj -997)뿐이다.
- 커널 문서 기준 이해로는 overcommit 0(heuristic)은 한 번의 할당이 RAM+스왑을 넘는 "명백한 초과"만 거부하므로 점진적으로 커지는 폭주 프로세스는 막지 못한다(이 호스트에서 직접 시험하지는 않았다).

선택지:

- **A (권장)**: CP-7은 건너뛴다(CIS 4.2.6 예외로 문서화). overcommit 값은 강제하지 않는다 — 한 번도 적용된 적이 없어 켜면 검증되지 않은 동작 변경이다. 대신 효과가 큰 쪽을 한다: 인프라 Pod(Traefik, Prometheus, Grafana, Calico, MetalLB, hostpath-provisioner 등)에 메모리 request=limit(Guaranteed)을 지정한다. `99-oom-hardening.conf`는 실제로 적용되지 않는다는 사실을 주석에 적거나 지운다(거짓 안심 방지).
- B: overcommit 0을 실제로 적용하려면 kubelet이 덮어쓴 **뒤에** 다시 써야 한다. 시작 직후 실행되는 `ExecStartPost`는 kubelet보다 먼저 실행되어 다시 덮이므로 소용이 없다(이전 문서의 제안은 틀렸다). kubelite에 `PartOf`로 묶은 별도 oneshot 유닛이 시작 후 수십 초 뒤에 `sysctl -w`를 실행하는 식이어야 한다. 위 이유로 권장하지 않는다.
- C: OOM 대응(0)을 포기하고 CP-7 적용. 실제 사고에 대한 대응 의도였으므로 권장하지 않는다.

스크립트는 `APPLY_KERNEL=1`일 때 이 충돌을 감지하면 거부한다(`FORCE_KERNEL=1`로만 우회).

## 이번 범위 밖

- **H-1 MySQL LoadBalancer 제거**: `fm`, `fm_dev`, `fma`의 `.env` 3곳이 `FM_DB_HOST=10.10.10.4`를 쓴다. ClusterIP로 바꾸면 이 값들을 함께 바꿔야 한다.
- **감사 로그 보호**: `/var/log/apiserver`는 호스트 root 소유(0750)이고 외부로 보내지 않는다. 장기 보관이나 변조 방지가 필요하면 별도로 정한다.
