#!/bin/bash 

cd ~/k8s


kubectl create namespace feedmaker

# volume
echo "applying fm-volume"
kubectl apply -f fm-volume.yml

# nginx
echo "installing nginx by helm"
helm install web bitnami/nginx -n feedmaker --version 18.3.5 --create-namespace --set staticSitePVC=public-html-pvc --set replicaCount=1 -f web-nginx-values.yml

# deployments
echo "installing mysql by helm"
helm install fm-db bitnami/mysql -n feedmaker --create-namespace --version 9.19.1 --set auth.rootPassword=micro170762 --set auth.database=feedmaker --set auth.username=feedmaker --set auth.password=micro170433 --set volumePermissions.enabled=true --set primary.persistence.enabled=true --set primary.persistence.existingClaim=mysql-pvc --set primary.service.type=LoadBalancer --set primary.livenessProbe.timeoutSeconds=5 --set primary.terminationGracePeriodSeconds=60
echo "initializing"
kubectl exec -i fm-db-mysql-0 -- mysql -u feedmaker feedmaker -pmicro170433 < ~/workspace/fm/init.sql

echo "applying fm-configmap"
kubectl apply -f fm-configmap.yml
echo "applying fm-deployment"
kubectl apply -f fm-deployment.yml

# browserless
helm install fm skm/browserless-chrome -n feedmaker --create-namespace --set replicaCount=2

# ingress
echo "applying fm-ingress"
kubectl apply -f fm-ingress.yml

