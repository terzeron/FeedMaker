#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""k8s/fm-deployment.yml 의 백엔드 컨테이너 보안 설정을 검증한다.

PyYAML 의존성을 추가하지 않고 test_nginx_security.py 와 동일하게 텍스트로 파싱한다.
readOnlyRootFilesystem 을 켠 뒤에도 동작하도록, 컨테이너 로깅은 파일이 아닌 stdout 으로
나가야 한다(logging.docker.conf). 호스트 CLI 는 repo 의 logging.conf(파일 핸들러)를 쓴다.
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent
DEPLOYMENT = ROOT / "k8s" / "fm-deployment.yml"
DOCKERFILE = ROOT / "backend" / "Dockerfile"
LOGGING_CONF = ROOT / "logging.conf"
LOGGING_DOCKER_CONF = ROOT / "logging.docker.conf"


def _backend_deployment_block() -> str:
    """fm-backend Deployment 문서만 잘라낸다 (frontend 의 동일 지시어와 섞이지 않도록)."""
    docs = DEPLOYMENT.read_text(encoding="utf-8").split("\n---")
    for doc in docs:
        if "kind: Deployment" in doc and "name: fm-backend" in doc and "app: fm-backend-app" in doc:
            return doc
    raise AssertionError("fm-backend Deployment 문서를 찾지 못했다")


class TestBackendReadOnlyRootFilesystem:
    def setup_method(self):
        self.block = _backend_deployment_block()

    def test_read_only_root_filesystem_enabled(self):
        assert "readOnlyRootFilesystem: true" in self.block, "백엔드 컨테이너에 readOnlyRootFilesystem: true 가 없다"

    def test_no_privilege_escalation(self):
        assert "allowPrivilegeEscalation: false" in self.block

    def test_drops_all_capabilities(self):
        assert "drop:" in self.block and "- ALL" in self.block

    def test_home_redirected_to_tmp(self):
        # rootfs RO 에서 fontconfig·chromium 등 네이티브 라이브러리의 $HOME 기반 쓰기를
        # writable emptyDir(/tmp)로 보내기 위해 HOME=/tmp 가 설정돼야 한다
        assert "name: HOME" in self.block and "value: /tmp" in self.block, "HOME=/tmp 가 설정되지 않았다"

    def test_no_log_file_volume(self):
        # 로그는 stdout 으로 나가므로 로그용 파일 볼륨/마운트가 있으면 안 된다 (설정 표류 방지)
        assert "/app/logs" not in self.block, "로그 파일 마운트(/app/logs)가 남아 있다 — 로깅은 stdout 이어야 한다"


class TestContainerLoggingToStdout:
    def test_docker_logging_conf_has_no_file_handler(self):
        """컨테이너 로깅 설정은 파일 핸들러 없이 stdout 으로만 출력해야 rootfs 쓰기가 없다."""
        conf = LOGGING_DOCKER_CONF.read_text(encoding="utf-8")
        assert "TimedRotatingFileHandler" not in conf, "컨테이너 로깅에 파일 핸들러가 있다 (rootfs 쓰기 위험)"
        assert "FileHandler" not in conf, "컨테이너 로깅에 파일 핸들러가 있다 (rootfs 쓰기 위험)"
        assert "StreamHandler" in conf and "sys.stdout" in conf, "컨테이너 로깅이 stdout 으로 나가지 않는다"

    def test_dockerfile_uses_container_logging_conf(self):
        """Dockerfile 이 컨테이너용 stdout 설정을 /app/logging.conf 로 복사해야 한다."""
        df = DOCKERFILE.read_text(encoding="utf-8")
        assert "COPY logging.docker.conf /app/logging.conf" in df, "Dockerfile 이 logging.docker.conf 를 사용하지 않는다"

    def test_docker_console_handler_level_is_info(self):
        """컨테이너엔 파일 핸들러가 없어 console 이 곧 stdout 이고, feed 파이프라인이 그 stdout 을
        HTML content 로 캡처한다(Process.exec_cmd). console 을 DEBUG 로 두면 DEBUG 로그가 생성
        HTML 을 오염시키므로, 호스트 logging.conf 와 동일하게 INFO 여야 한다."""
        import configparser

        parser = configparser.RawConfigParser()
        parser.read(LOGGING_DOCKER_CONF, encoding="utf-8")
        assert parser.get("handler_consoleHandler", "level") == "INFO", "컨테이너 consoleHandler 가 INFO 가 아니다 — DEBUG 면 생성 HTML 이 오염된다"

    def test_host_logging_conf_keeps_file_handler(self):
        """호스트 CLI 용 logging.conf 는 기존 파일 로깅(run.log) 동작을 유지해야 한다."""
        conf = LOGGING_CONF.read_text(encoding="utf-8")
        assert "TimedRotatingFileHandler" in conf
        assert "'run.log'" in conf, "호스트 logging.conf 의 로그 경로가 바뀌었다 (CLI 부작용 위험)"
