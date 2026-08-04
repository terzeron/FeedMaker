#!/bin/bash 

cd ~/k8s

# DB credentials must be provided via environment (do NOT hardcode here).
: "${MYSQL_PASSWORD:?set MYSQL_PASSWORD before running}"
: "${MYSQL_ROOT_PASSWORD:?set MYSQL_ROOT_PASSWORD before running}"


kubectl create namespace feedmaker

# volume
echo "applying fm-volume"
kubectl apply -f fm-volume.yml

# nginx
echo "installing nginx by helm"
helm install web bitnami/nginx -n feedmaker --version 18.3.5 --create-namespace --set staticSitePVC=public-html-pvc --set replicaCount=1 -f web-nginx-values.yml

# deployments
# 자격증명을 helm --set 으로 넘기면 `ps` 와 helm release values 에 평문으로 남는다.
# secret 을 stdin(heredoc) 으로 먼저 만들고 helm 은 auth.existingSecret 으로 참조한다.
echo "creating mysql credential secret"
kubectl create secret generic fm-db-mysql -n feedmaker --from-env-file=/dev/stdin <<EOF
mysql-root-password=$MYSQL_ROOT_PASSWORD
mysql-password=$MYSQL_PASSWORD
EOF

echo "installing mysql by helm"
# service.type 은 LoadBalancer 유지 — 로컬/LAN 에서 DB 직접 접근이 필요하다.
# resources 를 반드시 지정한다. chart 기본값이 비어 있어 그대로 두면 QoS BestEffort
# (oom_score_adj 1000) 가 되고, 호스트 메모리 고갈 시 DB 가 가장 먼저 죽는다
# (2026-08-04 OOM storm 에서 실제로 kill 됨).
#   - requests == limits 로 QoS Guaranteed(adj -997) 확보
#   - volumePermissions initContainer 도 함께 지정해야 한다. QoS 판정은 init container 를
#     포함하므로 하나라도 비면 Guaranteed 가 되지 않는다.
#   - 1Gi 근거: 10일 관측 peak 444MiB + 여유 2.3배 / 500m 근거: peak 26m + 넉넉한 여유
helm install fm-db bitnami/mysql -n feedmaker --create-namespace --version 9.19.1 --set auth.existingSecret=fm-db-mysql --set auth.database=feedmaker --set auth.username=feedmaker --set volumePermissions.enabled=true --set primary.persistence.enabled=true --set primary.persistence.existingClaim=mysql-pvc --set primary.service.type=LoadBalancer --set primary.livenessProbe.timeoutSeconds=5 --set primary.terminationGracePeriodSeconds=60 \
  --set primary.resources.requests.memory=1Gi --set primary.resources.requests.cpu=500m \
  --set primary.resources.limits.memory=1Gi --set primary.resources.limits.cpu=500m \
  --set volumePermissions.resources.requests.memory=128Mi --set volumePermissions.resources.requests.cpu=100m \
  --set volumePermissions.resources.limits.memory=128Mi --set volumePermissions.resources.limits.cpu=100m
echo "initializing"
# mysql -p"$PW" 는 클라이언트 경고 + 노출을 유발하므로 MYSQL_PWD 환경변수로 전달한다.
kubectl exec -i fm-db-mysql-0 -n feedmaker -- env MYSQL_PWD="$MYSQL_PASSWORD" mysql -u feedmaker feedmaker < ~/workspace/fm/init.sql

echo "applying fm-configmap"
kubectl apply -f fm-configmap.yml
echo "applying fm-deployment"
kubectl apply -f fm-deployment.yml

# browserless
# TODO: resources 를 지정해야 한다 (현재 BestEffort, oom_score_adj 1000).
#   10일 관측 peak: memory 188MiB / cpu 39m → requests 256Mi·100m, limits 1Gi·1 권장.
#   skm repo 가 helm repo list 에 없어 chart 의 values 키를 확인할 수 없었다.
#   repo 복구 후 `helm show values skm/browserless-chrome` 로 키를 확인해 --set 을 추가할 것.
#   그 전까지는 live Deployment 에 kubectl patch 로 적용된 상태이며, 이 스크립트를
#   다시 실행하면 되돌아간다.
helm install fm skm/browserless-chrome -n feedmaker --create-namespace --set replicaCount=2

# ingress
echo "applying fm-ingress"
kubectl apply -f fm-ingress.yml

