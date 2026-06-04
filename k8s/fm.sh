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
helm install fm-db bitnami/mysql -n feedmaker --create-namespace --version 9.19.1 --set auth.existingSecret=fm-db-mysql --set auth.database=feedmaker --set auth.username=feedmaker --set volumePermissions.enabled=true --set primary.persistence.enabled=true --set primary.persistence.existingClaim=mysql-pvc --set primary.service.type=LoadBalancer --set primary.livenessProbe.timeoutSeconds=5 --set primary.terminationGracePeriodSeconds=60
echo "initializing"
# mysql -p"$PW" 는 클라이언트 경고 + 노출을 유발하므로 MYSQL_PWD 환경변수로 전달한다.
kubectl exec -i fm-db-mysql-0 -n feedmaker -- env MYSQL_PWD="$MYSQL_PASSWORD" mysql -u feedmaker feedmaker < ~/workspace/fm/init.sql

echo "applying fm-configmap"
kubectl apply -f fm-configmap.yml
echo "applying fm-deployment"
kubectl apply -f fm-deployment.yml

# browserless
helm install fm skm/browserless-chrome -n feedmaker --create-namespace --set replicaCount=2

# ingress
echo "applying fm-ingress"
kubectl apply -f fm-ingress.yml

