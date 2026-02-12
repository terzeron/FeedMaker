#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""의존성 모듈 API 호환성 테스트

dependabot이 의존성을 업데이트할 때 응용 코드가 영향을 받는지 자동으로 검증한다.
각 의존성 모듈의 실제 사용 API를 테스트한다.
"""

import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path


def _can_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except (ImportError, OSError):
        return False


# ---------------------------------------------------------------------------
# 1. BeautifulSoup4
# ---------------------------------------------------------------------------
class TestBeautifulSoup4(unittest.TestCase):
    def test_parse_html(self) -> None:
        from bs4 import BeautifulSoup

        html = "<html><body><div class='a'>hello</div><div class='b'>world</div></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        self.assertIsNotNone(soup.body)

    def test_find_all(self) -> None:
        from bs4 import BeautifulSoup

        html = "<ul><li>1</li><li>2</li><li>3</li></ul>"
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("li")
        self.assertEqual(len(items), 3)

    def test_tag_types(self) -> None:
        from bs4 import BeautifulSoup, Comment, NavigableString, Tag

        html = "<div>text<!-- comment --></div>"
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div")
        self.assertIsInstance(div, Tag)
        children = list(div.children)
        self.assertIsInstance(children[0], NavigableString)
        self.assertIsInstance(children[1], Comment)

    def test_attribute_access(self) -> None:
        from bs4 import BeautifulSoup

        html = '<a href="https://example.com" class="link">click</a>'
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("a")
        self.assertEqual(tag.get("href"), "https://example.com")
        self.assertTrue(tag.has_attr("class"))
        self.assertEqual(tag.name, "a")


# ---------------------------------------------------------------------------
# 2. FastAPI
# ---------------------------------------------------------------------------
class TestFastAPI(unittest.TestCase):
    def test_app_creation_and_route(self) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/test")
        def read_test():
            return {"message": "ok"}

        client = TestClient(app)
        resp = client.get("/test")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"message": "ok"})

    def test_http_exception(self) -> None:
        from fastapi import FastAPI, HTTPException
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/err")
        def raise_err():
            raise HTTPException(status_code=404, detail="not found")

        client = TestClient(app)
        resp = client.get("/err")
        self.assertEqual(resp.status_code, 404)

    def test_json_response(self) -> None:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        from fastapi.testclient import TestClient

        app = FastAPI()

        @app.get("/json")
        def json_resp():
            return JSONResponse(content={"key": "value"}, status_code=201)

        client = TestClient(app)
        resp = client.get("/json")
        self.assertEqual(resp.status_code, 201)

    def test_cors_middleware(self) -> None:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware

        app = FastAPI()
        app.add_middleware(CORSMiddleware, allow_origins=["*"])
        # middleware 등록 자체가 성공하면 OK
        self.assertTrue(len(app.user_middleware) > 0)


# ---------------------------------------------------------------------------
# 3. FileLock
# ---------------------------------------------------------------------------
class TestFileLock(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_context_manager(self) -> None:
        from filelock import FileLock

        lock_path = os.path.join(self.tmpdir, "test.lock")
        lock = FileLock(lock_path)
        with lock:
            self.assertTrue(lock.is_locked)
        self.assertFalse(lock.is_locked)

    def test_timeout_exception(self) -> None:
        from filelock import FileLock, Timeout

        lock_path = os.path.join(self.tmpdir, "test2.lock")
        lock1 = FileLock(lock_path)
        lock2 = FileLock(lock_path)
        with lock1:
            with self.assertRaises(Timeout):
                lock2.acquire(timeout=0.1)


# ---------------------------------------------------------------------------
# 4. mail1
# ---------------------------------------------------------------------------
class TestMail1(unittest.TestCase):
    def test_import(self) -> None:
        import mail1
        self.assertTrue(hasattr(mail1, "send"))


# ---------------------------------------------------------------------------
# 5. OrderedSet
# ---------------------------------------------------------------------------
class TestOrderedSet(unittest.TestCase):
    def test_creation_and_order(self) -> None:
        from ordered_set import OrderedSet

        s = OrderedSet([3, 1, 2, 1, 3])
        self.assertEqual(list(s), [3, 1, 2])

    def test_add_and_membership(self) -> None:
        from ordered_set import OrderedSet

        s = OrderedSet()
        s.add("a")
        s.add("b")
        s.add("a")
        self.assertIn("a", s)
        self.assertEqual(len(s), 2)
        self.assertEqual(list(s), ["a", "b"])


# ---------------------------------------------------------------------------
# 6. pdf2image
# ---------------------------------------------------------------------------
@unittest.skipUnless(_can_import("pdf2image"), "pdf2image not available")
class TestPdf2Image(unittest.TestCase):
    def test_import_and_callable(self) -> None:
        from pdf2image import convert_from_path
        self.assertTrue(callable(convert_from_path))


# ---------------------------------------------------------------------------
# 7. pdftotext
# ---------------------------------------------------------------------------
@unittest.skipUnless(_can_import("pdftotext"), "pdftotext not available")
class TestPdftotext(unittest.TestCase):
    def test_import_and_pdf_class(self) -> None:
        import pdftotext
        self.assertTrue(hasattr(pdftotext, "PDF"))


# ---------------------------------------------------------------------------
# 8. Pillow
# ---------------------------------------------------------------------------
class TestPillow(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_new_and_save(self) -> None:
        from PIL import Image

        img = Image.new("RGB", (100, 50), color=(255, 0, 0))
        self.assertEqual(img.size, (100, 50))
        path = os.path.join(self.tmpdir, "test.png")
        img.save(path)
        self.assertTrue(os.path.exists(path))

    def test_open_and_resize(self) -> None:
        from PIL import Image

        img = Image.new("RGB", (200, 100))
        path = os.path.join(self.tmpdir, "src.png")
        img.save(path)

        opened = Image.open(path)
        resized = opened.resize((100, 50), Image.Resampling.LANCZOS)
        self.assertEqual(resized.size, (100, 50))

    def test_convert(self) -> None:
        from PIL import Image

        img = Image.new("RGBA", (10, 10))
        converted = img.convert("RGB")
        self.assertEqual(converted.mode, "RGB")

    def test_frombytes(self) -> None:
        from PIL import Image

        data = bytes([0] * (10 * 10 * 3))
        img = Image.frombytes("RGB", (10, 10), data)
        self.assertEqual(img.size, (10, 10))

    def test_image_ops(self) -> None:
        from PIL import Image, ImageOps

        img = Image.new("RGB", (50, 50))
        # exif_transpose는 EXIF 데이터 없어도 동작해야 함
        result = ImageOps.exif_transpose(img)
        self.assertIsNotNone(result)

    def test_unidentified_image_error(self) -> None:
        from PIL import Image, UnidentifiedImageError

        bad_path = os.path.join(self.tmpdir, "bad.png")
        with open(bad_path, "w") as f:
            f.write("not an image")
        with self.assertRaises(UnidentifiedImageError):
            with Image.open(bad_path) as img:
                img.load()


# ---------------------------------------------------------------------------
# 9. psutil
# ---------------------------------------------------------------------------
class TestPsutil(unittest.TestCase):
    def test_process_iter(self) -> None:
        import psutil

        procs = list(psutil.process_iter(["pid", "name"]))
        self.assertTrue(len(procs) > 0)

    def test_current_process(self) -> None:
        import psutil

        p = psutil.Process(os.getpid())
        info = p.as_dict(attrs=["pid", "name"])
        self.assertEqual(info["pid"], os.getpid())

    def test_no_such_process(self) -> None:
        import psutil

        with self.assertRaises(psutil.NoSuchProcess):
            psutil.Process(999999999).name()


# ---------------------------------------------------------------------------
# 10. pyheif
# ---------------------------------------------------------------------------
@unittest.skipUnless(_can_import("pyheif"), "pyheif not available")
class TestPyheif(unittest.TestCase):
    def test_import_and_read_callable(self) -> None:
        import pyheif
        self.assertTrue(callable(pyheif.read))


# ---------------------------------------------------------------------------
# 11. python-dateutil
# ---------------------------------------------------------------------------
class TestPythonDateutil(unittest.TestCase):
    def test_parser_parse(self) -> None:
        from dateutil import parser

        dt = parser.parse("2024-01-15T10:30:00+09:00")
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 15)

    def test_isoparser(self) -> None:
        from dateutil.parser import isoparser

        dt = isoparser().isoparse("2024-06-01T12:00:00Z")
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 6)


# ---------------------------------------------------------------------------
# 12. PyRSS2Gen
# ---------------------------------------------------------------------------
class TestPyRSS2Gen(unittest.TestCase):
    def test_rss_item(self) -> None:
        import datetime
        import PyRSS2Gen

        item = PyRSS2Gen.RSSItem(
            title="Test Item",
            link="https://example.com",
            description="desc",
            pubDate=datetime.datetime(2024, 1, 1),
        )
        self.assertEqual(item.title, "Test Item")

    def test_rss2_write_xml(self) -> None:
        import datetime
        import PyRSS2Gen

        rss = PyRSS2Gen.RSS2(
            title="Test Feed",
            link="https://example.com",
            description="A test feed",
            lastBuildDate=datetime.datetime(2024, 1, 1),
            items=[
                PyRSS2Gen.RSSItem(
                    title="Item 1",
                    link="https://example.com/1",
                    description="desc1",
                ),
            ],
        )
        buf = io.BytesIO()
        rss.write_xml(buf)
        xml_content = buf.getvalue()
        self.assertIn(b"<title>Test Feed</title>", xml_content)
        self.assertIn(b"<title>Item 1</title>", xml_content)


# ---------------------------------------------------------------------------
# 13. Requests
# ---------------------------------------------------------------------------
class TestRequests(unittest.TestCase):
    def test_get_post_callable(self) -> None:
        import requests

        self.assertTrue(callable(requests.get))
        self.assertTrue(callable(requests.post))
        self.assertTrue(callable(requests.head))

    def test_exception_classes(self) -> None:
        import requests

        self.assertTrue(issubclass(requests.ConnectionError, requests.RequestException))
        self.assertTrue(issubclass(requests.Timeout, requests.RequestException))
        self.assertTrue(issubclass(requests.HTTPError, requests.RequestException))

    def test_cookies_jar(self) -> None:
        from requests.cookies import RequestsCookieJar

        jar = RequestsCookieJar()
        jar.set("name", "value")
        self.assertEqual(jar.get("name"), "value")


# ---------------------------------------------------------------------------
# 14. resvg-py
# ---------------------------------------------------------------------------
class TestResvgPy(unittest.TestCase):
    def test_svg_to_bytes(self) -> None:
        import resvg_py

        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="red"/></svg>'
        png_data = resvg_py.svg_to_bytes(svg)
        self.assertIsInstance(png_data, bytes)
        # PNG signature
        self.assertTrue(png_data[:4] == b"\x89PNG")


# ---------------------------------------------------------------------------
# 15. Selenium
# ---------------------------------------------------------------------------
class TestSelenium(unittest.TestCase):
    def test_imports(self) -> None:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions

        self.assertTrue(hasattr(webdriver, "Chrome"))
        self.assertTrue(hasattr(By, "ID"))
        self.assertTrue(hasattr(By, "CSS_SELECTOR"))
        self.assertTrue(callable(expected_conditions.presence_of_element_located))
        self.assertTrue(callable(expected_conditions.invisibility_of_element_located))

    def test_chrome_options(self) -> None:
        from selenium.webdriver import ChromeOptions

        options = ChromeOptions()
        options.add_argument("--headless")
        self.assertIn("--headless", options.arguments)

    def test_exception_classes(self) -> None:
        from selenium.common.exceptions import (
            InvalidCookieDomainException,
            NoAlertPresentException,
            TimeoutException,
            WebDriverException,
        )

        self.assertTrue(issubclass(TimeoutException, WebDriverException))
        self.assertTrue(issubclass(InvalidCookieDomainException, WebDriverException))
        self.assertTrue(issubclass(NoAlertPresentException, WebDriverException))


# ---------------------------------------------------------------------------
# 16. SQLAlchemy
# ---------------------------------------------------------------------------
class TestSQLAlchemy(unittest.TestCase):
    def test_engine_and_session(self) -> None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine("sqlite:///:memory:")
        Session = sessionmaker(bind=engine)
        session = Session()
        self.assertIsNotNone(session)
        session.close()
        engine.dispose()

    def test_url_create(self) -> None:
        from sqlalchemy import URL

        url = URL.create(
            drivername="sqlite",
            database=":memory:",
        )
        self.assertIn("sqlite", str(url))

    def test_declarative_model_and_crud(self) -> None:
        from sqlalchemy import String, create_engine
        from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

        class Base(DeclarativeBase):
            pass

        class TestModel(Base):
            __tablename__ = "test_table"
            id: Mapped[int] = mapped_column(primary_key=True)
            name: Mapped[str] = mapped_column(String(50))

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)

        # Create
        with Session() as session:
            obj = TestModel(id=1, name="test")
            session.add(obj)
            session.commit()

        # Read
        with Session() as session:
            result = session.query(TestModel).filter_by(name="test").first()
            self.assertIsNotNone(result)
            self.assertEqual(result.name, "test")

        # Update
        with Session() as session:
            result = session.query(TestModel).filter_by(id=1).first()
            result.name = "updated"
            session.commit()

        with Session() as session:
            result = session.query(TestModel).filter_by(id=1).first()
            self.assertEqual(result.name, "updated")

        # Delete
        with Session() as session:
            result = session.query(TestModel).filter_by(id=1).first()
            session.delete(result)
            session.commit()

        with Session() as session:
            result = session.query(TestModel).filter_by(id=1).first()
            self.assertIsNone(result)

        engine.dispose()

    def test_event_listener(self) -> None:
        from sqlalchemy import create_engine, event

        engine = create_engine("sqlite:///:memory:")
        called = []

        @event.listens_for(engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            called.append(True)

        with engine.connect():
            pass

        self.assertTrue(len(called) > 0)
        engine.dispose()

    def test_sql_functions(self) -> None:
        from sqlalchemy import and_, func, or_

        self.assertTrue(callable(func.count))
        expr_and = and_(True, True)
        expr_or = or_(True, False)
        self.assertIsNotNone(expr_and)
        self.assertIsNotNone(expr_or)


# ---------------------------------------------------------------------------
# 17. urllib3
# ---------------------------------------------------------------------------
class TestUrllib3(unittest.TestCase):
    def test_disable_warnings(self) -> None:
        import urllib3

        # 호출 자체가 에러 없이 성공해야 함
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def test_insecure_request_warning(self) -> None:
        from urllib3.exceptions import InsecureRequestWarning

        self.assertTrue(issubclass(InsecureRequestWarning, Warning))


# ---------------------------------------------------------------------------
# 18. Uvicorn
# ---------------------------------------------------------------------------
class TestUvicorn(unittest.TestCase):
    def test_import_and_run_callable(self) -> None:
        import uvicorn

        self.assertTrue(callable(uvicorn.run))


# ---------------------------------------------------------------------------
# 19. python-dotenv
# ---------------------------------------------------------------------------
class TestPythonDotenv(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_load_dotenv(self) -> None:
        from dotenv import load_dotenv

        env_path = os.path.join(self.tmpdir, ".env")
        with open(env_path, "w") as f:
            f.write("TEST_DEP_KEY=hello123\n")

        load_dotenv(env_path, override=True)
        self.assertEqual(os.environ.get("TEST_DEP_KEY"), "hello123")
        # cleanup
        os.environ.pop("TEST_DEP_KEY", None)

    def test_dotenv_values(self) -> None:
        from dotenv import dotenv_values

        env_path = os.path.join(self.tmpdir, ".env")
        with open(env_path, "w") as f:
            f.write("A=1\nB=two\n")

        values = dotenv_values(env_path)
        self.assertEqual(values["A"], "1")
        self.assertEqual(values["B"], "two")


# ---------------------------------------------------------------------------
# 20. lxml
# ---------------------------------------------------------------------------
class TestLxml(unittest.TestCase):
    def test_import(self) -> None:
        import lxml
        self.assertIsNotNone(lxml)

    def test_bs4_lxml_parser(self) -> None:
        from bs4 import BeautifulSoup

        html = "<html><body><p>test</p></body></html>"
        soup = BeautifulSoup(html, "lxml")
        self.assertEqual(soup.find("p").text, "test")


# ---------------------------------------------------------------------------
# 21. PyMySQL
# ---------------------------------------------------------------------------
class TestPyMySQL(unittest.TestCase):
    def test_import(self) -> None:
        import pymysql
        self.assertIsNotNone(pymysql)

    def test_sqlalchemy_url_creation(self) -> None:
        from sqlalchemy import URL

        url = URL.create(
            drivername="mysql+pymysql",
            username="user",
            password="pass",
            host="localhost",
            port=3306,
            database="testdb",
        )
        self.assertIn("pymysql", str(url))
        self.assertIn("localhost", str(url))


if __name__ == "__main__":
    unittest.main()
