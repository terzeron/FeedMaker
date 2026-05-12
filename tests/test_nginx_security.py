#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""frontend/default.conf 의 보안 헤더 설정을 검증한다."""

from pathlib import Path
import re

NGINX_CONF = Path(__file__).parent.parent / "frontend" / "default.conf"


def _get_conf_text() -> str:
    return NGINX_CONF.read_text(encoding="utf-8")


def _extract_header_value(conf: str, header_name: str) -> str | None:
    """conf 텍스트에서 add_header <name> "<value>" [always]; 를 파싱한다."""
    pattern = rf'add_header\s+{re.escape(header_name)}\s+"([^"]+)"'
    m = re.search(pattern, conf, re.IGNORECASE)
    return m.group(1) if m else None


def _extract_index_html_block(conf: str) -> str:
    """location = /index.html { ... } 블록의 내용을 추출한다.

    nginx add_header는 자식 location에 동일 지시어가 있으면 부모를 상속하지
    않으므로, index.html 블록을 별도로 검증해야 한다.
    """
    m = re.search(r"location\s*=\s*/index\.html\s*\{([^}]*)\}", conf, re.DOTALL)
    return m.group(1) if m else ""


class TestNginxSecurityHeaders:
    def setup_method(self):
        self.conf = _get_conf_text()

    def test_x_content_type_options(self):
        val = _extract_header_value(self.conf, "X-Content-Type-Options")
        assert val == "nosniff", f"X-Content-Type-Options expected 'nosniff', got {val!r}"

    def test_x_frame_options(self):
        val = _extract_header_value(self.conf, "X-Frame-Options")
        assert val == "DENY", f"X-Frame-Options expected 'DENY', got {val!r}"

    def test_referrer_policy(self):
        val = _extract_header_value(self.conf, "Referrer-Policy")
        assert val == "strict-origin-when-cross-origin"

    def test_permissions_policy_present(self):
        assert "Permissions-Policy" in self.conf

    def test_csp_present(self):
        csp = _extract_header_value(self.conf, "Content-Security-Policy")
        assert csp is not None, "Content-Security-Policy header not found"

    def test_csp_default_src_self(self):
        csp = _extract_header_value(self.conf, "Content-Security-Policy")
        assert "default-src 'self'" in csp

    def test_csp_frame_ancestors_none(self):
        """클릭재킹 방지: frame-ancestors 'none'"""
        csp = _extract_header_value(self.conf, "Content-Security-Policy")
        assert "frame-ancestors 'none'" in csp

    def test_csp_object_src_none(self):
        """플러그인 실행 차단: object-src 'none'"""
        csp = _extract_header_value(self.conf, "Content-Security-Policy")
        assert "object-src 'none'" in csp

    def test_csp_base_uri_self(self):
        """base tag 인젝션 방지: base-uri 'self'"""
        csp = _extract_header_value(self.conf, "Content-Security-Policy")
        assert "base-uri 'self'" in csp

    def test_csp_form_action_self(self):
        csp = _extract_header_value(self.conf, "Content-Security-Policy")
        assert "form-action 'self'" in csp

    def test_csp_allows_facebook_sdk_script(self):
        """Facebook SDK 로드 허용: script-src에 connect.facebook.net 포함"""
        csp = _extract_header_value(self.conf, "Content-Security-Policy")
        assert "https://connect.facebook.net" in csp

    def test_csp_allows_api_connect(self):
        """백엔드 API 요청 허용: connect-src에 api-fm.terzeron.com 포함"""
        csp = _extract_header_value(self.conf, "Content-Security-Policy")
        assert "https://api-fm.terzeron.com" in csp

    def test_csp_allows_bootstrap_cdn_style(self):
        """Bootstrap CDN 허용: style-src에 cdn.jsdelivr.net 포함"""
        csp = _extract_header_value(self.conf, "Content-Security-Policy")
        assert "https://cdn.jsdelivr.net" in csp

    def test_csp_no_unsafe_eval(self):
        """eval() 차단 확인: unsafe-eval 없음"""
        csp = _extract_header_value(self.conf, "Content-Security-Policy")
        assert "unsafe-eval" not in csp

    def test_headers_have_always_directive(self):
        """에러 응답(4xx/5xx)에도 헤더가 전송되어야 함"""
        required = ["X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy"]
        for name in required:
            pattern = rf'add_header\s+{re.escape(name)}\s+"[^"]+"\s+always'
            assert re.search(pattern, self.conf, re.IGNORECASE), f"{name} is missing 'always' directive"

    def test_no_deprecated_x_xss_protection(self):
        """폐기된 X-XSS-Protection 헤더가 없어야 한다."""
        assert "X-XSS-Protection" not in self.conf, "X-XSS-Protection is deprecated and must be removed"


class TestNginxIndexHtmlSecurityHeaders:
    """location = /index.html 블록에도 보안 헤더가 존재하는지 검증한다.

    nginx add_header 상속 규칙: 자식 location에 add_header 지시어가 하나라도
    있으면 부모 server 블록의 add_header가 상속되지 않는다. index.html 블록은
    Cache-Control 헤더를 선언하므로 보안 헤더를 명시적으로 반복해야 한다.
    """

    def setup_method(self):
        conf = _get_conf_text()
        self.block = _extract_index_html_block(conf)
        assert self.block, "location = /index.html block not found in default.conf"

    def test_block_exists(self):
        assert self.block, "location = /index.html block must exist"

    def test_csp_in_index_html_block(self):
        csp = _extract_header_value(self.block, "Content-Security-Policy")
        assert csp is not None, "Content-Security-Policy missing from location = /index.html block"
        assert "default-src 'self'" in csp

    def test_x_frame_options_in_index_html_block(self):
        val = _extract_header_value(self.block, "X-Frame-Options")
        assert val == "DENY", f"X-Frame-Options missing or wrong in location = /index.html block: {val!r}"

    def test_x_content_type_options_in_index_html_block(self):
        val = _extract_header_value(self.block, "X-Content-Type-Options")
        assert val == "nosniff", f"X-Content-Type-Options missing or wrong in location = /index.html block: {val!r}"

    def test_referrer_policy_in_index_html_block(self):
        val = _extract_header_value(self.block, "Referrer-Policy")
        assert val == "strict-origin-when-cross-origin", f"Referrer-Policy missing in location = /index.html block: {val!r}"

    def test_security_headers_have_always_in_index_html_block(self):
        """index.html 블록 내 보안 헤더에도 always 지시어가 있어야 함"""
        required = ["X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy"]
        for name in required:
            pattern = rf'add_header\s+{re.escape(name)}\s+"[^"]+"\s+always'
            assert re.search(pattern, self.block, re.IGNORECASE), f"{name} is missing 'always' directive in location = /index.html block"

    def test_no_x_xss_protection_in_index_html_block(self):
        """폐기된 헤더가 index.html 블록에도 없어야 함"""
        assert "X-XSS-Protection" not in self.block
