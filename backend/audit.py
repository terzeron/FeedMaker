#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""보안 감사(audit) 로깅.

인증/인가 이벤트와 관리자 작업을 구조화(JSON)된 한 줄 로그로 남긴다.
`request_id_var`로 요청 단위 상관관계(correlation)를 부여한다.
"""

import json
import logging
from contextvars import ContextVar
from typing import Any, Optional

from fastapi import Request

# 전용 audit 로거. loggers 설정에 없으면 root로 propagate되어 동일 핸들러에 기록된다.
_AUDIT_LOGGER = logging.getLogger("audit")

# 요청 단위 상관 ID. 미들웨어가 set/reset 한다.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def audit_log(event: str, *, email: str = "-", outcome: str = "-", request: Optional[Request] = None, resource: str = "-", **extra: Any) -> None:
    """감사 이벤트 한 건을 구조화 로그로 남긴다.

    event: login_success / login_failed / login_locked / login_denied / logout / admin_action / admin_denied 등
    """
    # audit 로깅 실패가 요청 처리(인증/인가)를 깨뜨려선 안 되므로 전체를 방어적으로 처리한다.
    try:
        client_ip = "-"
        method = "-"
        path = resource
        if request is not None:
            client = getattr(request, "client", None)
            client_ip = str(getattr(client, "host", "-")) if client else "-"
            method = str(getattr(request, "method", "-"))
            url = getattr(request, "url", None)
            path = str(getattr(url, "path", resource)) if url is not None else resource

        record: dict[str, Any] = {"event": str(event), "email": str(email), "outcome": str(outcome), "ip": client_ip, "method": method, "path": path, "request_id": request_id_var.get()}
        record.update(extra)
        _AUDIT_LOGGER.info("AUDIT %s", json.dumps(record, ensure_ascii=False, default=str))
    except Exception as e:  # pragma: no cover - 방어적
        _AUDIT_LOGGER.warning("audit_log failed for event=%s: %s", event, e)
