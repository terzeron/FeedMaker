#!/bin/bash
# CIS-HARDENING-PLAN.md CP-1~CP-7 적용 스크립트 (microk8s 단일 노드).
#
# 반드시 sudo 로 실행: sudo bash k8s/cis-hardening-apply.sh   (미리보기는 sudo 없이 DRY_RUN=1)
# 순서와 근거는 CIS-APPLY-RUNBOOK.md 를 본다.
#
# apiserver/kubelet 플래그를 바꾼 뒤에는 `systemctl restart snap.microk8s.daemon-kubelite` 로 재기동한다.
# kubelite 는 apiserver, kubelet, scheduler, controller-manager, proxy 를 한 프로세스로 돌리므로 이것으로 충분하고
# containerd 는 건드리지 않으므로 컨테이너는 계속 실행될 것으로 예상한다(API가 20초쯤 끊긴다).
# 예전 버전은 `microk8s stop/start` 를 썼는데, 이는 containerd 까지 멈춰 모든 컨테이너를 재시작시킨다.
#
# 단계 게이팅(환경변수):
#   APPLY_AUDIT=1       CP-4  apiserver 감사 로그(audit-policy.yaml)                    [기본 ON]
#   APPLY_ADMISSION=1   CP-5  NodeRestriction admission 플러그인 + feedmaker PSS 라벨    [기본 ON]
#   APPLY_ANON=1        CP-2  apiserver --anonymous-auth=false                          [기본 OFF]
#                             감사 로그로 system:anonymous 사용처를 확인한 뒤에 켠다(런북 3단계).
#   APPLY_KUBELET_AUTHZ=1 CP-3 kubelet --authorization-mode=Webhook                     [기본 OFF]
#   APPLY_RBAC=1        CP-1  `microk8s enable rbac`. 이미 RBAC 이면 건너뛴다.            [기본 OFF]
#   APPLY_KERNEL=1      CP-7  kubelet --protect-kernel-defaults=true                    [기본 OFF]
#                             /etc/sysctl.d 의 vm.overcommit_memory 와 충돌하면 거부한다(FORCE_KERNEL=1 로 무시).
#   APPLY_BASELINE=1    (호환용) APPLY_AUDIT 와 APPLY_ADMISSION 의 기본값을 정한다. CP-2 는 더 이상 포함하지 않는다.
#   DRY_RUN=1           파일을 바꾸지 않고 바뀔 내용만 출력한다(sudo 불필요).
#   CP-6(약한 cipher 제거)는 이미 적용돼 있어 생략한다.
#
# 예) 1단계(감사 + NodeRestriction):  sudo bash k8s/cis-hardening-apply.sh
#     3단계(익명 접근 차단):          sudo APPLY_AUDIT=0 APPLY_ADMISSION=0 APPLY_ANON=1 bash k8s/cis-hardening-apply.sh
#
# 롤백: 각 args 파일은 *.bak.<timestamp> 로 백업된다. 재시작 후 API가 안 뜨면 이 스크립트가 백업을 복원하고
#       한 번 더 재기동한다. 수동 복구는 `cp -a <file>.bak.<ts> <file> && systemctl restart snap.microk8s.daemon-kubelite`.
set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
if [[ "${DRY_RUN}" != "1" && "${EUID}" -ne 0 ]]; then
  echo "ERROR: sudo 로 실행하세요: sudo bash $0  (미리보기: DRY_RUN=1 bash $0)" >&2
  exit 1
fi

SNAP_DATA="/var/snap/microk8s/current"
ARGS_DIR="${SNAP_DATA}/args"
APISERVER="${ARGS_DIR}/kube-apiserver"
KUBELET="${ARGS_DIR}/kubelet"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TS="$(date +%F-%H%M%S)"
KUBECTL=(kubectl)
command -v microk8s >/dev/null 2>&1 && KUBECTL=(microk8s kubectl)

APPLY_BASELINE="${APPLY_BASELINE:-1}"
APPLY_AUDIT="${APPLY_AUDIT:-${APPLY_BASELINE}}"
APPLY_ADMISSION="${APPLY_ADMISSION:-${APPLY_BASELINE}}"
APPLY_ANON="${APPLY_ANON:-0}"
APPLY_KUBELET_AUTHZ="${APPLY_KUBELET_AUTHZ:-0}"
APPLY_RBAC="${APPLY_RBAC:-0}"
APPLY_KERNEL="${APPLY_KERNEL:-0}"
FORCE_KERNEL="${FORCE_KERNEL:-0}"

NEED_RESTART=0
BACKUPS=()

say() { echo "$@"; }
backup() {
  [[ -f "$1" ]] || return 0
  if [[ "${DRY_RUN}" == "1" ]]; then say "  (dry-run) backup: $1.bak.${TS}"; return 0; fi
  # 같은 파일을 여러 단계에서 백업해도 첫 번째(원본)만 남긴다.
  [[ -f "$1.bak.${TS}" ]] && return 0
  cp -a "$1" "$1.bak.${TS}" && BACKUPS+=("$1") && say "  backup: $1.bak.${TS}"
}

# 인자 파일에 --flag=value 를 idempotent 하게 설정한다.
set_flag() {
  local file="$1" flag="$2" value="$3" cur=""
  cur="$(grep -E "^${flag}=" "$file" | head -1 || true)"
  if [[ "${DRY_RUN}" == "1" ]]; then
    say "  (dry-run) ${file##*/}: ${cur:-<없음>}  ->  ${flag}=${value}"
    return 0
  fi
  if [[ -n "$cur" ]]; then
    sed -i "s|^${flag}=.*|${flag}=${value}|" "$file"
  else
    echo "${flag}=${value}" >> "$file"
  fi
  say "  set: ${flag}=${value}  (${file##*/})"
}

# --enable-admission-plugins 에 플러그인을 추가한다(기존 값 보존).
add_admission_plugin() {
  local plugin="$1" cur
  cur="$(grep -E '^--enable-admission-plugins=' "$APISERVER" | head -1 | cut -d= -f2- || true)"
  if [[ -z "$cur" ]]; then
    set_flag "$APISERVER" "--enable-admission-plugins" "$plugin"
  elif [[ ",${cur}," == *",${plugin},"* ]]; then
    say "  already: --enable-admission-plugins 에 ${plugin} 있음 (${cur})"
  else
    set_flag "$APISERVER" "--enable-admission-plugins" "${plugin},${cur}"
  fi
}

api_ready() { "${KUBECTL[@]}" get --raw /readyz >/dev/null 2>&1; }

restart_kubelite() {
  if [[ "${DRY_RUN}" == "1" ]]; then say "  (dry-run) systemctl restart snap.microk8s.daemon-kubelite"; return 0; fi
  say "== kubelite 재기동 (API 약 20초 중단, containerd 는 그대로) =="
  systemctl restart snap.microk8s.daemon-kubelite
  local i
  for i in $(seq 1 36); do sleep 5; api_ready && { say "  API ready (${i}x5s)"; return 0; }; done
  return 1
}

rollback_all() {
  say "!! 재기동 후 API가 180초 안에 준비되지 않았다. 백업을 복원하고 다시 재기동한다."
  local f
  for f in "${BACKUPS[@]}"; do cp -a "${f}.bak.${TS}" "$f" && say "  restored: $f"; done
  systemctl restart snap.microk8s.daemon-kubelite
  local i
  for i in $(seq 1 36); do sleep 5; api_ready && { say "  복원 후 API ready. 원인은 'journalctl -u snap.microk8s.daemon-kubelite -n 80' 로 확인."; return 0; }; done
  say "!! 복원 후에도 API가 준비되지 않았다. 수동 확인 필요: journalctl -u snap.microk8s.daemon-kubelite -n 80"
}

echo "== CIS hardening apply (audit=${APPLY_AUDIT} admission=${APPLY_ADMISSION} anon=${APPLY_ANON} kubelet-authz=${APPLY_KUBELET_AUTHZ} rbac=${APPLY_RBAC} kernel=${APPLY_KERNEL} dry-run=${DRY_RUN}) =="

# ---- 사전 점검 -------------------------------------------------------------
[[ -f "${APISERVER}" && -f "${KUBELET}" ]] || { echo "ERROR: ${ARGS_DIR} 에 kube-apiserver/kubelet 인자 파일이 없다" >&2; exit 1; }
if [[ "${APPLY_AUDIT}" == "1" ]]; then
  python3 -c "import yaml,sys; d=yaml.safe_load(open(sys.argv[1])); assert d['kind']=='Policy' and d['rules']" "${REPO_DIR}/audit-policy.yaml" \
    || { echo "ERROR: audit-policy.yaml 이 올바른 Policy 가 아니다(잘못된 정책이면 apiserver 가 기동하지 못한다)" >&2; exit 1; }
  say "  audit-policy.yaml 문법 OK"
fi
if [[ "${APPLY_KERNEL}" == "1" ]]; then
  bad=0
  chk() { local k="$1" want="$2" got; got="$(sysctl -n "$k" 2>/dev/null || echo '?')"; [[ "$got" == "$want" ]] || { say "  불일치: $k 현재=$got 요구=$want"; bad=1; }; }
  chk vm.overcommit_memory 1; chk vm.panic_on_oom 0; chk kernel.panic 10; chk kernel.panic_on_oops 1
  chk kernel.keys.root_maxkeys 1000000; chk kernel.keys.root_maxbytes 25000000
  persisted="$(grep -hE '^\s*vm\.overcommit_memory\s*=' /etc/sysctl.d/*.conf /etc/sysctl.conf 2>/dev/null | tail -1 | tr -d ' ' || true)"
  if [[ -n "${persisted}" && "${persisted}" != "vm.overcommit_memory=1" ]]; then
    say "  충돌: /etc/sysctl.d 는 ${persisted} 로 영구 설정하는데 kubelet 은 protect-kernel-defaults=true 일 때 1 을 요구한다."
    say "        (OOM 폭주 대응으로 0 을 의도한 설정이면 CP-7 과 양립할 수 없다. CIS-APPLY-RUNBOOK.md 참고)"
    [[ "${FORCE_KERNEL}" == "1" ]] || bad=1
  fi
  [[ "${bad}" == "0" ]] || { echo "ERROR: CP-7 사전 점검 실패 -> 적용하지 않는다(재부팅 후 kubelet 이 기동하지 못할 수 있다)" >&2; exit 1; }
fi

# ---- 적용 ------------------------------------------------------------------
if [[ "${APPLY_AUDIT}" == "1" ]]; then
  echo "[CP-4] apiserver audit log (Metadata 정책, 잡음 제거 규칙 포함)"
  backup "${APISERVER}"
  if [[ "${DRY_RUN}" != "1" ]]; then
    install -d -m 0750 /var/log/apiserver
    cp -a "${REPO_DIR}/audit-policy.yaml" "${ARGS_DIR}/audit-policy.yaml"
  else
    say "  (dry-run) cp audit-policy.yaml -> ${ARGS_DIR}/audit-policy.yaml ; install -d /var/log/apiserver"
  fi
  set_flag "${APISERVER}" "--audit-log-path" "/var/log/apiserver/audit.log"
  set_flag "${APISERVER}" "--audit-log-maxage" "30"
  set_flag "${APISERVER}" "--audit-log-maxbackup" "10"
  set_flag "${APISERVER}" "--audit-log-maxsize" "100"
  set_flag "${APISERVER}" "--audit-policy-file" "${ARGS_DIR}/audit-policy.yaml"
  NEED_RESTART=1
fi

if [[ "${APPLY_ADMISSION}" == "1" ]]; then
  echo "[CP-5] NodeRestriction admission 플러그인(kubelet 이 자기 노드/파드 외 객체를 못 바꾸게 한다)"
  backup "${APISERVER}"
  add_admission_plugin NodeRestriction
  NEED_RESTART=1
  echo "[CP-5] feedmaker PSS 라벨 — 이미 enforce=baseline + warn/audit=restricted 이면 변화 없음(enforce 는 건드리지 않는다)"
  if [[ "${DRY_RUN}" == "1" ]]; then say "  (dry-run) label ns feedmaker warn/audit=restricted"; else
    "${KUBECTL[@]}" label ns feedmaker pod-security.kubernetes.io/warn=restricted pod-security.kubernetes.io/audit=restricted --overwrite
  fi
fi

if [[ "${APPLY_ANON}" == "1" ]]; then
  echo "[CP-2] apiserver --anonymous-auth=false (익명 /readyz 등이 401 이 된다. 먼저 감사 로그로 사용처를 확인했는가?)"
  backup "${APISERVER}"
  set_flag "${APISERVER}" "--anonymous-auth" "false"
  NEED_RESTART=1
fi

if [[ "${APPLY_KUBELET_AUTHZ}" == "1" ]]; then
  echo "[CP-3] kubelet --authorization-mode=Webhook (kubelet API 호출마다 apiserver RBAC 로 인가)"
  backup "${KUBELET}"
  set_flag "${KUBELET}" "--authorization-mode" "Webhook"
  NEED_RESTART=1
fi

if [[ "${APPLY_KERNEL}" == "1" ]]; then
  echo "[CP-7] kubelet --protect-kernel-defaults=true"
  backup "${KUBELET}"
  set_flag "${KUBELET}" "--protect-kernel-defaults" "true"
  NEED_RESTART=1
fi

if [[ "${NEED_RESTART}" == "1" ]]; then
  restart_kubelite || { rollback_all; exit 1; }
fi

if [[ "${APPLY_RBAC}" == "1" ]]; then
  if grep -qE '^--authorization-mode=.*RBAC' "${APISERVER}"; then
    echo "[CP-1] 이미 RBAC 가 켜져 있다 -> 건너뜀 ($(grep -E '^--authorization-mode=' "${APISERVER}"))"
  elif [[ "${DRY_RUN}" == "1" ]]; then
    say "[CP-1] (dry-run) microk8s enable rbac 후 'systemctl restart snap.microk8s.daemon-kubelite' 가 추가로 필요하다"
  else
    echo "[CP-1] microk8s enable rbac (인자만 바뀐다. apiserver 는 아래에서 재기동해야 적용된다)"
    microk8s enable rbac || true
    restart_kubelite || { rollback_all; exit 1; }
  fi
fi

[[ "${DRY_RUN}" == "1" ]] && { echo "== dry-run 끝. 변경된 것은 없다. =="; exit 0; }

# ---- 검증 ------------------------------------------------------------------
echo
echo "== 검증 =="
echo "-- 인자 --"
grep -E "^--(authorization-mode|anonymous-auth|enable-admission-plugins|audit-)" "${APISERVER}" || true
grep -E "^--(authorization-mode|anonymous-auth|protect-kernel)" "${KUBELET}" || true
if [[ "${APPLY_ANON}" == "1" ]]; then
  code="$(curl -sk -o /dev/null -w '%{http_code}' -m 5 https://127.0.0.1:16443/readyz || true)"
  echo "-- 익명 /readyz = ${code} (401 이어야 정상; 예전 방식 'can-i --as=system:anonymous' 는 플래그와 무관하게 no 라 검증이 안 된다)"
fi
if [[ "${APPLY_AUDIT}" == "1" ]]; then
  sleep 3
  echo "-- 감사 로그: $(ls -l /var/log/apiserver/audit.log 2>&1 | awk '{print $5" bytes"}')  이벤트 $(wc -l < /var/log/apiserver/audit.log 2>/dev/null || echo 0)건"
fi
if [[ "${APPLY_KUBELET_AUTHZ}" == "1" ]]; then
  echo "-- kubelet Webhook 인가 경로(apiserver->kubelet, 토큰 클라이언트) --"
  "${KUBECTL[@]}" logs -n kube-system deploy/coredns --tail=1 >/dev/null 2>&1 && echo "  kubectl logs OK" || echo "  !! kubectl logs 실패(kubelet 인가 문제 의심)"
  "${KUBECTL[@]}" top nodes >/dev/null 2>&1 && echo "  kubectl top nodes OK" || echo "  !! kubectl top 실패(metrics-server -> kubelet 인가 문제 의심)"
fi
echo "-- 워크로드 정상성(비정상 Pod) --"
"${KUBECTL[@]}" get pods -A --no-headers | grep -vE 'Running|Completed' || echo "  비정상 Pod 없음"
echo "== 완료. 문제 시 *.bak.${TS} 로 복구 후 systemctl restart snap.microk8s.daemon-kubelite. =="
