from typing import Any, Optional, Dict, List, Union

class Mail:
    def __init__(self, **kwargs: Any) -> None: ...
    def send(self, to: Union[str, List[str]], subject: str, body: str, **kwargs: Any) -> bool: ...
    def connect(self) -> bool: ...
    def disconnect(self) -> None: ...

def send(
    subject: str,
    text: str,
    sender: str,
    recipients: List[str],
    smtp_host: Optional[str] = None,
    smtp_port: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any
) -> None: ...

def send_mail(
    to: Union[str, List[str]],
    subject: str,
    body: str,
    smtp_server: Optional[str] = None,
    smtp_port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    **kwargs: Any
) -> bool: ...

class MailError(Exception): ...
class SMTPError(MailError): ...
class AuthenticationError(MailError): ... 