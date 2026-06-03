# CIS Kubernetes Benchmark — microk8s 클러스터 Hardening 계획서

> 작성 근거: kube-bench(미지원)를 대신해 `/var/snap/microk8s/current/args/*` 를 직접
> 점검한 결과(2026-06-02). **모든 항목은 클러스터 설정 변경 + microk8s 재기동을 동반**하므로
> 레포 코드가 아니라 운영 작업이며, **승인 + 유지보수 창(maintenance window)** 에서 적용한다.
>
> 공통 적용 절차:
>
> 1. `sudo cp /var/snap/microk8s/current/args/<file>{,.bak.$(date +%F)}` ← 항상 백업
> 2. 인자 수정
> 3. `sudo microk8s stop && sudo microk8s start` (또는 `sudo snap restart microk8s.daemon-kubelite`)
> 4. 검증 명령 실행
>
> 적용 순서 권장: **CP-6/CP-7(저위험) → CP-2/CP-4 → CP-5 → CP-1/CP-3(RBAC, 최고위험)**
> RBAC 를 마지막에 두는 이유: 먼저 켜면 다른 변경의 검증 트래픽까지 막혀 원인 분리가 어려워진다.

| ID   | 항목                                                                   | 위험도     | 적용 난이도/리스크                |
| ---- | ---------------------------------------------------------------------- | ---------- | --------------------------------- |
| CP-1 | apiserver `--authorization-mode=AlwaysAllow` (RBAC 미동작)             | **High\*** | 높음 — 기존 워크로드 깨질 수 있음 |
| CP-2 | apiserver `--anonymous-auth` 미설정(기본 true)                         | High       | 낮음                              |
| CP-3 | kubelet `--authorization-mode` 미설정(기본 AlwaysAllow)                | Medium     | 중간 (RBAC 의존)                  |
| CP-4 | API 감사 로그 없음                                                     | Medium     | 중간 (디스크/정책파일)            |
| CP-5 | `--allow-privileged=true` + NodeRestriction/PodSecurity admission 없음 | Medium     | 중간                              |
| CP-6 | apiserver TLS 약한 cipher(3DES/CBC-SHA1) 포함                          | Low        | 낮음                              |
| CP-7 | kubelet `--protect-kernel-defaults` 미설정                             | Low        | 중간 (sysctl 선행 필요)           |

\* CP-1 실제 심각도는 apiserver(192.168.0.10:16443)가 LAN 내부 한정이라 Critical→High. LAN이 공유망이면 Critical로 복귀.

---

## CP-1 / CP-3 — RBAC 활성화 (최우선이자 최고위험)

microk8s 는 RBAC 를 꺼진 채 출하한다. addon 으로 켜면 apiserver `--authorization-mode` 가 `RBAC,Node` 로 바뀐다.

```bash
# 적용 전: 현재 클러스터에서 SA/롤바인딩 의존 워크로드 파악
kubectl get clusterrolebindings,rolebindings -A

microk8s enable rbac           # apiserver authorization-mode -> RBAC,Node
```

- **리스크**: RBAC 가 켜지면 적절한 Role/RoleBinding 이 없는 컴포넌트는 즉시 403. 특히 직접 만든
  컨트롤러/CI 토큰/헬름 릴리스가 깨질 수 있다. **반드시 유지보수 창에서, 롤백(`microk8s disable rbac`) 준비 후.**
- **CP-3(kubelet)**: RBAC 활성 후 kubelet args 에 `--authorization-mode=Webhook` 추가하면
  kubelet API 도 apiserver 인가를 거친다.
- **검증**:
  ```bash
  grep authorization-mode /var/snap/microk8s/current/args/kube-apiserver   # RBAC,Node
  kubectl auth can-i '*' '*' --as=system:anonymous   # -> no 여야 함
  ```

## CP-2 — apiserver anonymous-auth 비활성

```bash
# /var/snap/microk8s/current/args/kube-apiserver 에 추가
--anonymous-auth=false
```

- 리스크: 익명 health/liveness 의존 컴포넌트가 있으면 영향. 보통 낮음.
- 검증: `grep anonymous-auth .../kube-apiserver`

## CP-4 — API 감사 로그 (CSF Detect 갭 해소)

```bash
# 감사 정책 파일 생성 (예: .../args/audit-policy.yaml) — 최소 Metadata 레벨
# kube-apiserver 에 추가:
--audit-log-path=/var/log/apiserver/audit.log
--audit-log-maxage=30
--audit-log-maxbackup=10
--audit-log-maxsize=100
--audit-policy-file=${SNAP_DATA}/args/audit-policy.yaml
```

- 리스크: 디스크 사용량 증가. logrotate/maxsize 로 관리.

## CP-5 — 권한/Admission 강화

```bash
# 1) 네임스페이스 단위 Pod Security Standards (가장 안전, 즉효):
kubectl label ns feedmaker \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/warn=restricted
#    → 우리 워크로드는 이미 restricted 호환(runAsNonRoot/drop ALL/seccomp)이라 통과 예상.

# 2) apiserver admission 플러그인에 NodeRestriction 추가:
--enable-admission-plugins=EventRateLimit,NodeRestriction
```

- `--allow-privileged=true` 자체는 microk8s 일부 addon 이 요구하므로 끄지 말고,
  위 PSS enforce 로 "권한 컨테이너 생성"을 네임스페이스 레벨에서 차단하는 편이 안전.
- 검증: 권한 파드 생성 시도가 거부되는지 `kubectl run ... --privileged` 로 확인.

## CP-6 — apiserver 약한 cipher 제거

kubelet 은 이미 GCM/CHACHA 전용. apiserver 도 동일 수준으로:

```bash
# kube-apiserver --tls-cipher-suites 를 3DES/CBC-SHA1 제외한 GCM/CHACHA 목록으로 교체
--tls-cipher-suites=TLS_AES_128_GCM_SHA256,TLS_AES_256_GCM_SHA384,TLS_CHACHA20_POLY1305_SHA256,TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305,TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305
```

- 리스크: 매우 오래된 클라이언트 호환성. 내부 클러스터라 사실상 없음.

## CP-7 — kubelet protect-kernel-defaults

```bash
# 선행: 커널 sysctl 이 kubelet 기대값과 맞아야 기동됨. 안 맞으면 kubelet 이 안 뜬다.
--protect-kernel-defaults=true
```

- 리스크: 중간. **반드시 백업 + 즉시 롤백 가능 상태에서.** 단일노드라 영향 큼.

---

## H-1 — MySQL 외부 노출 축소 (LoadBalancer → ClusterIP)

`k8s_mysql.sh` / `fm.sh` 의 helm 설정이 `primary.service.type=LoadBalancer` 라 DB 가
metallb IP(10.10.10.4:3306) + NodePort(31273) 로 LAN 전체에 열려 있다.

```bash
# 신규 설치 시: --set primary.service.type=ClusterIP
# 기존 운영 서비스 즉시 전환:
kubectl patch svc fm-db-mysql -n feedmaker -p '{"spec":{"type":"ClusterIP"}}'
```

- 외부 DB 접근이 필요하면 `kubectl port-forward` 로 임시 터널. 상시 노출 금지.
- 같은 맥락에서 fm-backend/fm-frontend 도 게이트웨이가 라우팅하므로 NodePort 대신
  ClusterIP 로 충분한지 검토(현재 HTTPRoute 가 Service 를 직접 참조).

---

## 적용 후 재점검

```bash
# args 재확인
for f in kube-apiserver kubelet; do echo "== $f =="; sudo cat /var/snap/microk8s/current/args/$f; done
# 워크로드 정상성
kubectl -n feedmaker rollout status deploy/fm-backend deploy/fm-frontend
kubectl -n feedmaker get pods
# RBAC 동작
kubectl auth can-i '*' '*' --as=system:anonymous   # -> no
```
