# syntax=docker/dockerfile:1
FROM node:22.16.0 AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install -g npm@10.9.2 && npm install && npx browserslist@latest --update-db

ARG GIT_COMMIT=unknown
COPY frontend/ .
RUN GIT_COMMIT=$GIT_COMMIT npm run build


# non-root nginx: master/worker 모두 uid 101로 실행, pid/temp는 /tmp 사용.
# 8080(>=1024) 바인딩이므로 privileged port가 필요 없어 root 없이 동작한다.
FROM nginxinc/nginx-unprivileged:1.25

# base OS 보안 패치 적용 (apt는 root 필요 → 작업 후 비root로 복귀)
USER root
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/default.conf /etc/nginx/conf.d

# 명시적 비root 유저 (base 이미지가 uid 101 nginx 유저 제공)
# HTTP health는 slim 이미지에 curl/wget이 없으므로 k8s httpGet probe로 처리한다.
USER nginx

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
