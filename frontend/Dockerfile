# syntax=docker/dockerfile:1
FROM node:22.23.4@sha256:63538dfe497cc29dfafdda25ada09b46db68a3f4cc205abf1f5d6bf0913f3384 AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
# package.json engines가 npm>=11을 요구하고 .npmrc는 engine-strict=true이므로
# base 이미지 번들 npm(10.9.8)으로는 install이 EBADENGINE으로 실패한다.
# lockfile을 생성한 로컬 npm과 동일 버전으로 고정한다.
RUN npm install -g npm@11.19.0 && npm install && npx browserslist@latest --update-db

ARG GIT_COMMIT=unknown
COPY frontend/ .
RUN GIT_COMMIT=$GIT_COMMIT npm run build


# non-root nginx: master/worker 모두 uid 101로 실행, pid/temp는 /tmp 사용.
# 8080(>=1024) 바인딩이므로 privileged port가 필요 없어 root 없이 동작한다.
# nginx2root(CVE-2026-123007 외) 수정판 1.30.7이 nginx-unprivileged 이미지에 아직 없어
# 공식 nginx 이미지를 쓰고, nginx-unprivileged와 같은 방식으로 비root 실행을 직접 설정한다.
FROM nginx:1.30.7@sha256:8a7280c664b1a205092ffea6443299e6d307fe65b6f946b02028fa311c29fd01

# base OS 보안 패치 적용 (apt는 root 필요 → 작업 후 비root로 복귀)
# readOnlyRootFilesystem 호환: user 지시어 제거, pid와 temp 경로를 /tmp(emptyDir)로 옮긴다.
# load_module로 쓰지 않는 njs·xslt 모듈을 지워 libxml2(CVE-2026-6653, trixie 미수정)를 이미지에서 뺀다.
USER root
ARG APT_REFRESH=0
RUN : "apt refresh ${APT_REFRESH}" && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get purge -y --auto-remove nginx-module-njs nginx-module-xslt libxslt1.1 libxml2 && \
    ! dpkg -s libxml2 >/dev/null 2>&1 && \
    rm -rf /var/lib/apt/lists/* && \
    sed -i -e '/^user  nginx;/d' \
           -e 's,^pid .*,pid        /tmp/nginx.pid;,' \
           -e '/^http {/a\    client_body_temp_path /tmp/client_temp;\n    proxy_temp_path       /tmp/proxy_temp_path;\n    fastcgi_temp_path     /tmp/fastcgi_temp;\n    uwsgi_temp_path       /tmp/uwsgi_temp;\n    scgi_temp_path        /tmp/scgi_temp;' \
           /etc/nginx/nginx.conf

COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/default.conf /etc/nginx/conf.d

# 명시적 비root 유저 (base 이미지가 uid 101 nginx 유저 제공)
# HTTP health는 slim 이미지에 curl/wget이 없으므로 k8s httpGet probe로 처리한다.
USER nginx

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
