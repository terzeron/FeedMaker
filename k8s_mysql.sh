#!/bin/bash

# namespace 생성 및 변경
kubectl create namespace feedmaker
kubens feedmaker

# mysql 설치
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
# bitnami repository를 bitnamilegacy로 지정해야 함
helm install mysql bitnami/mysql \
  -n feedmaker \
  --create-namespace \
  --set image.registry=docker.io \
  --set image.repository=bitnamilegacy/mysql \
  --set image.tag=8.0.40-debian-12-r1 \
  --set auth.rootPassword=$MYSQL_ROOT_PASSWORD \
  --set auth.database=$MYSQL_DATABASE \
  --set auth.username=$MYSQL_USER \
  --set auth.password=$MYSQL_PASSWORD \
  --set primary.persistence.enabled=true \
  --set primary.persistence.size=8Gi
kubectl patch svc mysql -n feedmaker -p '{"spec":{"type":"LoadBalancer"}}'
kubectl get svc mysql -n feedmaker
mysql -h $FM_DB_HOST -P $FM_DB_PORT -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "show databases"

# 초기 데이터 로딩
echo "초기 데이터 로딩 중..."
python -c "from bin.problem_manager import ProblemManager; pm = ProblemManager(); pm.load_all()"
