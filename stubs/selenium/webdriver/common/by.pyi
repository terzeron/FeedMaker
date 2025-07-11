from typing import Any

class By:
    ID: str = "id"
    XPATH: str = "xpath"
    LINK_TEXT: str = "link text"
    PARTIAL_LINK_TEXT: str = "partial link text"
    NAME: str = "name"
    TAG_NAME: str = "tag name"
    CLASS_NAME: str = "class name"
    CSS_SELECTOR: str = "css selector"

def __getattr__(name: str) -> Any: ... 