#!/bin/bash 

# 이 스크립트가 쓰는 *.yml 은 이 파일과 같은 디렉터리에 있다.
cd "$(dirname "${BASH_SOURCE[0]}")"

# DB credentials must be provided via environment (do NOT hardcode here).
: "${MYSQL_PASSWORD:?set MYSQL_PASSWORD before running}"
: "${MYSQL_ROOT_PASSWORD:?set MYSQL_ROOT_PASSWORD before running}"


kubectl create namespace feedmaker

# volume
echo "applying fm-volume"
kubectl apply -f fm-volume.yml

# nginx (정적 파일 + feed 프록시). bitnami chart 대신 공식 nginx-unprivileged plain manifest를 쓴다.
# 정식 manifest는 클러스터 저장소(~/k8s/static_web/web-nginx.yaml)에 있다. Service web-nginx 는 별도로 두며
# 그 selector가 app.kubernetes.io/instance=web-oss 이다(처음 설치라면 아래 Service를 함께 만든다).
echo "applying web-nginx"
kubectl apply -f ~/k8s/static_web/web-nginx.yaml

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

# browserless는 2026-10에 제거했다(사용하지 않음). 이전에는 여기서 helm install fm skm/browserless-chrome 을 실행했다.

# ingress
echo "applying fm-ingress"
kubectl apply -f fm-ingress.yml

