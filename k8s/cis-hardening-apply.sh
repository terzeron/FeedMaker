#!/bin/bash
# CIS-HARDENING-PLAN.md CP-1~CP-7 적용 스크립트 (microk8s 단일 노드).
#
# 반드시 sudo 로 실행: sudo bash k8s/cis-hardening-apply.sh
# microk8s 재기동을 동반하므로 클러스터에 잠시 다운타임이 발생한다. 유지보수 창에서 실행할 것.
#
# 단계 게이팅(환경변수로 제어):
#   APPLY_BASELINE=1  CP-2(anonymous-auth) + CP-4(audit) + CP-5(PSS warn/audit)   [기본 ON, 저위험]
#   APPLY_RBAC=1      CP-1(RBAC enable) + CP-3(kubelet Webhook authz)              [기본 OFF, 고위험]
#   APPLY_KERNEL=1    CP-7(protect-kernel-defaults)                                [기본 OFF, 고위험]
#   CP-6(약한 cipher 제거)는 현재 클러스터에 이미 적용돼 있어 생략한다.
#
# 예) 저위험만:           sudo APPLY_BASELINE=1 bash k8s/cis-hardening-apply.sh
#     RBAC까지:           sudo APPLY_BASELINE=1 APPLY_RBAC=1 bash k8s/cis-hardening-apply.sh
#
# 롤백: 각 args 파일은 *.bak.<timestamp> 로 백업된다. 복구 후 `microk8s stop && microk8s start`.
#       RBAC 롤백은 `microk8s disable rbac`.
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: sudo 로 실행하세요: sudo bash $0" >&2
  exit 1
fi

SNAP_DATA="/var/snap/microk8s/current"
ARGS_DIR="${SNAP_DATA}/args"
APISERVER="${ARGS_DIR}/kube-apiserver"
KUBELET="${ARGS_DIR}/kubelet"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TS="$(date +%F-%H%M%S)"

APPLY_BASELINE="${APPLY_BASELINE:-1}"
APPLY_RBAC="${APPLY_RBAC:-0}"
APPLY_KERNEL="${APPLY_KERNEL:-0}"

NEED_RESTART=0

backup() { [[ -f "$1" ]] && cp -a "$1" "$1.bak.${TS}" && echo "  backup: $1.bak.${TS}"; }

# 인자 파일에 --flag=value 를 idempotent 하게 설정한다.
set_flag() {
  local file="$1" flag="$2" value="$3"
  if grep -qE "^${flag}=" "$file"; then
    sed -i "s|^${flag}=.*|${flag}=${value}|" "$file"
  else
    echo "${flag}=${value}" >> "$file"
  fi
  echo "  set: ${flag}=${value}  (${file##*/})"
}

echo "== CIS hardening apply (baseline=${APPLY_BASELINE} rbac=${APPLY_RBAC} kernel=${APPLY_KERNEL}) =="

if [[ "${APPLY_BASELINE}" == "1" ]]; then
  echo "[CP-2] apiserver --anonymous-auth=false"
  backup "${APISERVER}"
  set_flag "${APISERVER}" "--anonymous-auth" "false"

  echo "[CP-4] apiserver audit log (Metadata 정책)"
  install -d -m 0750 /var/log/apiserver
  cp -a "${REPO_DIR}/audit-policy.yaml" "${ARGS_DIR}/audit-policy.yaml"
  set_flag "${APISERVER}" "--audit-log-path" "/var/log/apiserver/audit.log"
  set_flag "${APISERVER}" "--audit-log-maxage" "30"
  set_flag "${APISERVER}" "--audit-log-maxbackup" "10"
  set_flag "${APISERVER}" "--audit-log-maxsize" "100"
  set_flag "${APISERVER}" "--audit-policy-file" "${ARGS_DIR}/audit-policy.yaml"
  NEED_RESTART=1

  echo "[CP-5] feedmaker 네임스페이스 PSS — warn/audit 만(비차단). enforce 는 helm 워크로드 호환성 확인 전까지 걸지 않는다."
  microk8s kubectl label ns feedmaker \
    pod-security.kubernetes.io/warn=restricted \
    pod-security.kubernetes.io/audit=restricted --overwrite
fi

if [[ "${APPLY_KERNEL}" == "1" ]]; then
  echo "[CP-7] kubelet --protect-kernel-defaults=true (주의: sysctl 불일치 시 kubelet 기동 실패 가능)"
  backup "${KUBELET}"
  set_flag "${KUBELET}" "--protect-kernel-defaults" "true"
  NEED_RESTART=1
fi

if [[ "${APPLY_RBAC}" == "1" ]]; then
  echo "[CP-3] kubelet --authorization-mode=Webhook"
  backup "${KUBELET}"
  set_flag "${KUBELET}" "--authorization-mode" "Webhook"
  NEED_RESTART=1
fi

if [[ "${NEED_RESTART}" == "1" ]]; then
  echo "== microk8s 재기동(다운타임 시작) =="
  microk8s stop
  microk8s start
  microk8s status --wait-ready --timeout 120 || true
fi

if [[ "${APPLY_RBAC}" == "1" ]]; then
  echo "[CP-1] microk8s enable rbac (authorization-mode -> RBAC,Node). 워크로드 깨지면 'microk8s disable rbac' 로 롤백."
  microk8s enable rbac
fi

echo
echo "== 검증 =="
echo "-- apiserver authorization-mode / anonymous-auth / audit --"
grep -E "authorization-mode|anonymous-auth|audit-" "${APISERVER}" || true
echo "-- kubelet authorization-mode / protect-kernel --"
grep -E "authorization-mode|protect-kernel|anonymous" "${KUBELET}" || true
echo "-- 익명 접근 거부 확인(no 여야 정상) --"
microk8s kubectl auth can-i '*' '*' --as=system:anonymous || true
echo "-- 워크로드 정상성 --"
microk8s kubectl -n feedmaker get pods
echo "-- PSS 라벨 --"
microk8s kubectl get ns feedmaker -o jsonpath='{.metadata.labels}{"\n"}'
echo "== 완료. 문제 시 *.bak.${TS} 로 복구 후 microk8s stop/start. =="
