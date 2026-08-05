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
# 설정은 전부 fm-db-mysql-values.yml 에 있다 (resources / image pin / service type 등).
# --set 으로 흩어두면 upgrade 때 빠뜨려 QoS 가 조용히 BestEffort 로 내려간다.
# upgrade 할 때도 반드시 같은 -f 를 넘길 것:
#   helm upgrade fm-db bitnami/mysql -n feedmaker --version 9.19.1 -f fm-db-mysql-values.yml
# 주의: 이 chart 는 auth.existingSecret 을 쓰는데도 upgrade 시 auth.rootPassword 를
#       요구한다. 자격증명을 --set 으로 넘기지 않으려면 upgrade 대신
#       `kubectl patch sts fm-db-mysql` 로 처리한다.
helm install fm-db bitnami/mysql -n feedmaker --create-namespace --version 9.19.1 -f fm-db-mysql-values.yml
echo "initializing"
# mysql -p"$PW" 는 클라이언트 경고 + 노출을 유발하므로 MYSQL_PWD 환경변수로 전달한다.
kubectl exec -i fm-db-mysql-0 -n feedmaker -- env MYSQL_PWD="$MYSQL_PASSWORD" mysql -u feedmaker feedmaker < ~/workspace/fm/init.sql

echo "applying fm-configmap"
kubectl apply -f fm-configmap.yml
echo "applying fm-deployment"
kubectl apply -f fm-deployment.yml

# browserless
helm install fm skm/browserless-chrome -n feedmaker --create-namespace --set replicaCount=2

# resources 를 helm values 가 아니라 설치 후 kubectl 로 지정한다.
# 이 chart(browserless-chrome 0.0.4)는 skm repo 가 사라져 `helm show values` 로
# resources 의 values 키를 확인할 수 없다. 확인 못 한 키를 --set 으로 추측해 넘기면
# 조용히 무시되므로, 결과가 검증되는 kubectl 로 처리한다.
# 지정하지 않으면 QoS BestEffort(oom_score_adj 1000) 라 호스트 메모리 고갈 시
# 가장 먼저 죽는다 (2026-08-04 OOM storm).
# 근거: 10일 관측 peak memory 188MiB / cpu 39m. Chrome 은 튈 수 있어 limits 는 넉넉히.
# skm repo 가 복구되면 `helm show values skm/browserless-chrome` 로 키를 확인해
# values 파일로 옮기는 것이 낫다.
echo "setting browserless resources"
kubectl -n feedmaker rollout status deploy/fm-browserless-chrome --timeout=180s
kubectl -n feedmaker set resources deploy/fm-browserless-chrome \
  --containers=browserless-chrome \
  --requests=memory=256Mi,cpu=100m --limits=memory=1Gi,cpu=1
kubectl -n feedmaker rollout status deploy/fm-browserless-chrome --timeout=180s

# ingress
echo "applying fm-ingress"
kubectl apply -f fm-ingress.yml

