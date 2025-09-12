#!/bin/bash

# namespace 생성 및 변경
kubectl create namespace feedmaker
kubens.sh feedmaker

# mysql 설치
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm install mysql bitnami/mysql --version 14.0.3 -n feedmaker --set auth.rootPassword="$MYSQL_ROOT_PASSWORD" --set auth.database="$MYSQL_DATABASE" --set auth.username="$MYSQL_USER" --set auth.password="$MYSQL_PASSWORD"

# mysql 호스트명 노출
ip=$(kubectl -n ingress-nginx get svc ingress-nginx-controller -o json | jq -r .status.loadBalancer.ingress\[0\].ip)
echo "IP: $ip"
grep $ip /etc/hosts > /dev/null && echo "You can use '$ip' as fixed service IP" || echo "no host name entry in /etc/hosts, you should add it"

# 초기 데이터 로딩
echo "초기 데이터 로딩 중..."
python -c "from bin.problem_manager import ProblemManager; pm = ProblemManager(); pm.load_all()"


# loki 설치
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install loki grafana/loki --version 6.40.0 -n feedmaker -f loki-values.yml

# loki용 ingress 설정
kubectl apply -f loki-ingress.yml
sleep 5

# 호스트명 등록 가이드
echo "다음 호스트명과 IP를 등록하세요"
kubectl get ingress loki-ingress -n feedmaker -o json | jq -r ".spec.rules[0].host"
kubectl get ingress loki-ingress -n feedmaker -o json | jq -r ".status.loadBalancer.ingress[0].ip"

