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
# DB는 ClusterIP로 유지 (외부 노출 금지). 외부 접근 필요 시 일시적으로 port-forward 사용:
#   kubectl port-forward -n feedmaker svc/mysql 13306:3306
kubectl get svc mysql -n feedmaker
# 검증도 in-cluster로 (host에서 직접 접속하지 않음)
kubectl exec -i -n feedmaker mysql-0 -- mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "show databases"

# 초기 데이터 로딩
echo "초기 데이터 로딩 중..."
python -c "from bin.problem_manager import ProblemManager; pm = ProblemManager(); pm.load_all()"
