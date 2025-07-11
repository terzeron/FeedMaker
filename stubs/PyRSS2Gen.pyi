from typing import Any, Optional, TextIO

class RSSItem:
    def __init__(
        self,
        title: Optional[str] = None,
        link: Optional[str] = None,
        description: Optional[str] = None,
        author: Optional[str] = None,
        categories: Optional[list[str]] = None,
        comments: Optional[str] = None,
        enclosure: Optional[Any] = None,
        guid: Optional[str] = None,
        pubDate: Optional[str] = None,
        source: Optional[str] = None,
        **kwargs: Any
    ) -> None: ...

class RSS2:
    def __init__(
        self,
        title: str,
        link: str,
        description: str,
        language: Optional[str] = None,
        copyright: Optional[str] = None,
        managingEditor: Optional[str] = None,
        webMaster: Optional[str] = None,
        pubDate: Optional[str] = None,
        lastBuildDate: Optional[str] = None,
        category: Optional[str] = None,
        generator: Optional[str] = None,
        docs: Optional[str] = None,
        cloud: Optional[str] = None,
        ttl: Optional[int] = None,
        image: Optional[Any] = None,
        textInput: Optional[Any] = None,
        skipHours: Optional[Any] = None,
        skipDays: Optional[Any] = None,
        items: Optional[list[RSSItem]] = None,
        **kwargs: Any
    ) -> None: ...
    
    def write_xml(self, outfile: TextIO, encoding: str = "iso-8859-1") -> None: ... 