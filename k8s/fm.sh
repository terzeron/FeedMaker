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
# groundhog2k chart 는 userDatabase 를 existingSecret 으로 넘기면 DB 이름과 사용자까지
# 그 secret 의 키에서 읽는다. 그래서 bitnami 시절의 2개(mysql-root-password /
# mysql-password)에 mysql-database / mysql-user 를 더한 4개 키가 필요하다.
# fm-deployment.yml 은 여전히 mysql-password 키만 참조하므로 그 이름은 바꾸지 않는다.
kubectl create secret generic fm-db-mysql -n feedmaker --from-env-file=/dev/stdin <<EOF
mysql-root-password=$MYSQL_ROOT_PASSWORD
mysql-password=$MYSQL_PASSWORD
mysql-database=${MYSQL_DATABASE:-feedmaker}
mysql-user=${MYSQL_USER:-feedmaker}
EOF

echo "installing mysql by helm"
# chart 를 bitnami/mysql 에서 groundhog2k/mysql 로 옮겼다. 이유는
# fm-db-mysql-values.yml 상단 주석 참고 (bitnami 이미지가 registry 에서 삭제됨).
# release 이름 fm-db 는 유지한다 — StatefulSet/Service 가 fm-db-mysql 로 그대로여서
# fm-deployment.yml 의 FM_DB_HOST 와 pod 이름 fm-db-mysql-0 이 바뀌지 않는다.
#
# 설정은 전부 fm-db-mysql-values.yml 에 있다 (resources / image pin / service type 등).
# --set 으로 흩어두면 upgrade 때 빠뜨려 QoS 가 조용히 BestEffort 로 내려간다.
# upgrade 할 때도 반드시 같은 -f 를 넘길 것:
#   helm upgrade fm-db groundhog2k/mysql -n feedmaker --version 3.1.4 -f fm-db-mysql-values.yml
helm repo add groundhog2k https://groundhog2k.github.io/helm-charts/
helm repo update groundhog2k
helm install fm-db groundhog2k/mysql -n feedmaker --create-namespace --version 3.1.4 -f fm-db-mysql-values.yml
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

