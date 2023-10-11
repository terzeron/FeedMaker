#!/usr/bin/env python

import sys
import os
import re
import time
import logging.config
from pathlib import Path
from typing import List, Dict, Any, Tuple, Callable, Optional
from shutil import which
from datetime import datetime, timedelta
from contextlib import suppress
import dateutil.parser
import PyRSS2Gen
from ordered_set import OrderedSet
from bin.crawler import Crawler, Method
from bin.extractor import Extractor
from bin.feed_maker_util import Config, URL, Datetime, Process, Data, PathUtil, FileManager, header_str
from bin.new_list_collector import NewListCollector
from bin.uploader import Uploader

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()
SECONDS_PER_DAY = 60 * 60 * 24


class FeedMaker:
    MAX_CONTENT_LENGTH = 64 * 1024
    MAX_NUM_DAYS = 7
    DEFAULT_WINDOW_SIZE = 5
    IMAGE_TAG_FMT_STR = "<img src='%s/img/1x1.jpg?feed=%s&item=%s'/>"

    def __init__(self, feed_dir_path: Path, do_collect_by_force: bool, do_collect_only: bool, rss_file_path: Path, window_size: int = DEFAULT_WINDOW_SIZE) -> None:
        LOGGER.debug(f"# FeedMaker(feed_dir_path={feed_dir_path}, do_collect_by_force={do_collect_by_force}, do_collect_only={do_collect_only}, rss_file_path={rss_file_path})")
        self.global_conf: Dict[str, Any] = Config.get_global_config()
        if not self.global_conf:
            LOGGER.error("Error: Can't get global configuration")
            return

        self.work_dir_path = Path(os.environ["FEED_MAKER_WORK_DIR"])
        self.feed_dir_path = feed_dir_path
        self.collection_conf: Dict[str, Any] = {}
        self.extraction_conf: Dict[str, Any] = {}
        self.rss_conf: Dict[str, Any] = {}
        self.do_collect_by_force = do_collect_by_force
        self.do_collect_only = do_collect_only
        self.rss_file_path = rss_file_path
        self.window_size = window_size

        self.list_dir = self.feed_dir_path / "newlist"
        self.html_dir = self.feed_dir_path / "html"
        self.img_dir_path = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"]) / "img"
        self.start_idx_file_path = self.feed_dir_path / "start_idx.txt"
        self.list_dir.mkdir(exist_ok=True)
        self.html_dir.mkdir(exist_ok=True)
        self.img_dir_path.mkdir(exist_ok=True)

    def __del__(self):
        del self.collection_conf
        del self.extraction_conf
        del self.rss_conf

    @staticmethod
    def get_image_tag_str(web_service_url: str, rss_file_name: str, item_url: str = "any_url") -> str:
        md5_name = URL.get_short_md5_name(URL.get_url_path(item_url))
        return FeedMaker.IMAGE_TAG_FMT_STR % (web_service_url, rss_file_name, md5_name)

    @staticmethod
    def get_size_of_template_with_image_tag(web_service_url: str, rss_file_name: str) -> int:
        return len(header_str) + len("\n") + len(FeedMaker.get_image_tag_str(web_service_url, rss_file_name)) + len("\n")

    @staticmethod
    def _is_image_tag_in_html_file(html_file_path: Path, image_tag_str: str) -> bool:
        is_image_tag_in_file: bool = False
        with html_file_path.open("r", encoding="utf-8") as infile:
            for line in infile:
                if image_tag_str in line:
                    is_image_tag_in_file = True
                    break
        return is_image_tag_in_file

    @staticmethod
    def _append_image_tag_to_html_file(html_file_path: Path, image_tag_str: str) -> None:
        with html_file_path.open("a", encoding="utf-8") as outfile:
            outfile.write("\n" + image_tag_str + "\n")

    @staticmethod
    def _get_size_of_template() -> int:
        return len(header_str) + 1

    @staticmethod
    def _get_html_file_path(html_dir: Path, link: str) -> Path:
        md5 = URL.get_short_md5_name(URL.get_url_path(link))
        return html_dir / f"{md5}.html"

    @staticmethod
    def _get_list_file_path(list_dir: Path, date_str: str) -> Path:
        return list_dir / f"{date_str}.txt"

    @staticmethod
    def _cmp_int_or_str(a: Dict[str, str], b: Dict[str, str]) -> int:
        m1 = re.search(r'^\d+$', a["sf"])
        m2 = re.search(r'^\d+$', b["sf"])

        if m1 and m2:
            ret = int(a["sf"]) - int(b["sf"])
        else:
            if a["sf"] < b["sf"]:
                ret = -1
            elif a["sf"] > b["sf"]:
                ret = 1
            else:
                ret = 0
        return ret

    @staticmethod
    def _cmp_to_key(mycmp) -> Callable[[Dict[str, Any]], Any]:
        # noinspection PyUnusedLocal,PyUnusedLocal
        class K:
            def __init__(self, obj, *_):
                self.obj = obj

            def __lt__(self, other):
                return mycmp(self.obj, other.obj) < 0

            def __gt__(self, other):
                return mycmp(self.obj, other.obj) > 0

            def __eq__(self, other):
                return mycmp(self.obj, other.obj) == 0

            def __le__(self, other):
                return mycmp(self.obj, other.obj) <= 0

            def __ge__(self, other):
                return mycmp(self.obj, other.obj) >= 0

            def __ne__(self, other):
                return mycmp(self.obj, other.obj) != 0

        return K

    def _read_old_feed_list_from_file(self) -> List[Tuple[str, str]]:
        LOGGER.debug("# _read_old_feed_list_from_file()")

        if not self.collection_conf:
            LOGGER.error("ERROR: can't get collection configuration")
            return []

        feed_list: List[Tuple[str, str]] = []
        dt = Datetime.get_current_time()
        if not self.collection_conf["is_completed"]:
            # 아직 진행 중인 피드에 대해서는 현재 날짜에 가장 가까운
            # 과거 리스트 파일 1개를 찾아서 그 안에 기록된 리스트를 꺼냄

            # 과거까지 리스트가 존재하는지 확인
            for i in range(self.MAX_NUM_DAYS):
                short_date_str = Datetime.get_short_date_str(dt - timedelta(days=i))
                list_file_path = FeedMaker._get_list_file_path(self.list_dir, short_date_str)
                # 오늘에 가장 가까운 리스트가 존재하면 탈출
                if list_file_path.is_file():
                    LOGGER.info(PathUtil.convert_path_to_str(list_file_path))
                    # read the old list
                    with list_file_path.open('r', encoding='utf-8') as in_file:
                        for line in in_file:
                            line = line.rstrip()
                            link, title = line.split("\t")
                            feed_list.append((link, title))
                        if feed_list:
                            break
        else:
            # 이미 완료된 피드에 대해서는 기존 리스트를 모두 취합함
            for entry in self.list_dir.iterdir():
                if entry.name.startswith(".") and entry.is_file():
                    continue

                file_path = self.list_dir / entry.name
                LOGGER.info(PathUtil.convert_path_to_str(file_path))
                with file_path.open('r', encoding='utf-8') as in_file:
                    for line in in_file:
                        line = line.rstrip()
                        link, title = line.split("\t")
                        feed_list.append((link, title))

        return Data.remove_duplicates(feed_list)

    def _make_html_file(self, item_url: str, title: str) -> bool:
        if not self.extraction_conf:
            LOGGER.error("ERROR: can't get extraction configuration")
            return False
        conf = self.extraction_conf

        html_file_path = FeedMaker._get_html_file_path(self.html_dir, item_url)
        if html_file_path.is_file():
            size = html_file_path.stat().st_size
        else:
            size = 0

        image_tag_str = FeedMaker.get_image_tag_str(self.global_conf["web_service_url"],
                                                    self.rss_file_path.name, item_url)

        if os.path.isfile(html_file_path) and size > FeedMaker.get_size_of_template_with_image_tag(self.global_conf["web_service_url"], self.rss_file_path.name):
            # 이미 성공적으로 만들어져 있으니까, 이미지 태그만 검사해보고 피드 리스트에 추가
            if FeedMaker._is_image_tag_in_html_file(html_file_path, image_tag_str):
                LOGGER.info(f"Old: {item_url}\t{title}\t{PathUtil.convert_path_to_str(html_file_path)} ({size} bytes > {self._get_size_of_template()} bytes of template)")
                ret = True
            else:
                LOGGER.error(f"Error: No image tag in html file '{PathUtil.convert_path_to_str(html_file_path)}'")
                LOGGER.debug(f"image tag: '{image_tag_str}'")
                LOGGER.warning(f"Warning: removing incomplete html file '{PathUtil.convert_path_to_str(html_file_path)}'")
                html_file_path.unlink(missing_ok=True)
                ret = False
        else:
            # 파일이 존재하지 않거나 크기가 작으니 다시 생성 시도
            crawler = Crawler(dir_path=self.feed_dir_path, render_js=conf["render_js"], method=Method.GET, headers=conf["headers"], timeout=conf["timeout"], num_retries=conf["num_retries"], encoding=conf["encoding"], verify_ssl=conf["verify_ssl"], copy_images_from_canvas=conf["copy_images_from_canvas"], simulate_scrolling=conf["simulate_scrolling"], disable_headless=conf["disable_headless"], blob_to_dataurl=conf["blob_to_dataurl"])
            option_str = Crawler.get_option_str(conf)
            crawler_cmd = f"crawler.py -f '{self.feed_dir_path}' {option_str} '{item_url}'"
            LOGGER.debug(f"cmd={crawler_cmd}")
            result, error, _ = crawler.run(item_url)
            if not result or error:
                LOGGER.error("Error: %s", error)
                return False

            content: Optional[str] = result
            if not conf.get("bypass_element_extraction", False):
                extraction_cmd = f"extractor.py -f '{self.feed_dir_path}' '{item_url}'"
                LOGGER.debug(f"cmd={extraction_cmd}")
                extractor = Extractor()
                content = extractor.extract_content(conf, item_url, input_data=result)
                del extractor
                if not content:
                    return False

            for post_process_script in conf["post_process_script_list"]:
                program = post_process_script.split(" ")[0]
                program_fullpath = which(program)
                if program_fullpath and program_fullpath.startswith(("/usr", "/bin", "/sbin")):
                    post_process_cmd = f"{post_process_script}"
                else:
                    post_process_cmd = f"{post_process_script} -f '{self.feed_dir_path}' '{item_url}'"
                LOGGER.debug(f"cmd={post_process_cmd}")
                result, error_msg = Process.exec_cmd(post_process_cmd, dir_path=self.feed_dir_path, input_data=content)
                LOGGER.debug(f"cmd={post_process_cmd}")
                if not result:
                    LOGGER.error(f"Error: No result in executing command '{post_process_cmd}")
                    return False
                if error_msg:
                    LOGGER.error("Error: %s", error_msg)
                    return False
                content = result

            LOGGER.debug(f"writing to '{html_file_path}'")
            with html_file_path.open("w", encoding="utf-8") as outfile:
                outfile.write(str(content))

            if conf["force_sleep_between_articles"]:
                time.sleep(5)

            if html_file_path.is_file():
                size = html_file_path.stat().st_size
            else:
                size = 0

            if size > self._get_size_of_template():
                if not FeedMaker._is_image_tag_in_html_file(html_file_path, image_tag_str):
                    FeedMaker._append_image_tag_to_html_file(html_file_path, image_tag_str)

                # 피드 리스트에 추가
                LOGGER.info(f"New: {item_url}\t{title}\t{PathUtil.convert_path_to_str(html_file_path)} ({size} bytes > {self._get_size_of_template()} bytes of template)")
                ret = True
            else:
                # 피드 리스트에서 제외
                LOGGER.warning(f"Warning: excluded {item_url}\t{title}\t{PathUtil.convert_path_to_str(html_file_path)} ({size} bytes <= {self._get_size_of_template()} bytes of template)")
                ret = False

        if "threshold_to_remove_html_with_incomplete_image" in conf:
            incomplete_image_list = FileManager.get_incomplete_image_list(html_file_path)
            if conf["threshold_to_remove_html_with_incomplete_image"] < len(incomplete_image_list):
                feed_img_dir_path = self.img_dir_path / self.feed_dir_path.name
                FileManager.remove_image_files_with_zero_size(feed_img_dir_path)
                FileManager.remove_html_file_without_cached_image_files(html_file_path)
                ret = False

        return ret

    def _get_idx_data(self) -> Tuple[int, int, Optional[datetime]]:
        LOGGER.debug("# get_idx_data()")

        if self.start_idx_file_path.is_file():
            with self.start_idx_file_path.open('r', encoding='utf-8') as in_file:
                line = in_file.readline()
                m = re.search(r'(?P<start_idx>\d+)\t(?P<mtime>\S+)', line)
                if m:
                    start_idx = int(m.group("start_idx"))
                    mtime_str = m.group("mtime")
                    end_idx = start_idx + self.window_size
                    mtime = dateutil.parser.parse(mtime_str)
                    return start_idx, end_idx, mtime

        # 처음 생성 시, 또는 파일에 정보가 없을 때
        start_idx = 1
        end_idx = start_idx + self.window_size
        mtime = Datetime.get_current_time()
        _, current_time_str = self._write_idx_data(start_idx, mtime, True)
        if not current_time_str:
            return 0, 0, None
        return start_idx, end_idx, mtime

    def _write_idx_data(self, start_idx: int, mtime: datetime, do_write_initially: bool = False) -> Tuple[int, Optional[str]]:
        LOGGER.debug(f"# write_idx_data(start_idx={start_idx}, mtime={mtime})")

        current_time = Datetime.get_current_time()
        delta = current_time - mtime
        increment_size = int((delta.total_seconds() * self.collection_conf["unit_size_per_day"]) / 86400)
        LOGGER.debug(f"start_idx={start_idx}, current time={current_time}, mtime={mtime}, self.window_size={self.window_size}, increment_size={increment_size}")
        next_start_idx = 1
        current_time_str = None
        if do_write_initially or increment_size > 0:
            next_start_idx = start_idx + increment_size
            with self.start_idx_file_path.open('w', encoding='utf-8') as out_file:
                current_time_str = Datetime.get_current_time_str()
                out_file.write(f"{next_start_idx}\t{current_time_str}\n")
        return next_start_idx, current_time_str

    def _fetch_old_feed_list_window(self, old_feed_list: List[Tuple[str, str]]) -> Optional[List[Tuple[str, str]]]:
        LOGGER.debug(f"# _fetch_old_feed_list_window(old_feed_list={old_feed_list}")
        # 오름차순 정렬
        feed_id_sort_field_list: List[Dict[str, Any]] = []
        feed_item_existence_set: OrderedSet[str] = OrderedSet([])

        matched_count = 0
        sort_field_pattern = self.collection_conf.get("sort_field_pattern", "")
        if not sort_field_pattern:
            LOGGER.error("Error: Can't get sort_field_pattern from collection_conf")
            return None

        for i, item in enumerate(old_feed_list):
            link, title = item
            m = re.search(sort_field_pattern, link + "\t" + title)
            if m:
                sort_field = m.group(1)
                with suppress(IndexError):
                    if m.group(2):
                        sort_field += " " + m.group(2)
                matched_count += 1
            else:
                sort_field = "999999999"

            if link not in feed_item_existence_set:
                # 번호 to 기준필드 정보를 저장해둠
                feed_id_sort_field = {"id": i, "sf": sort_field}
                feed_item_existence_set.add(link)
                feed_id_sort_field_list.append(feed_id_sort_field)

        # 전체 리스트 중 절반 이상의 정렬필드를 검출하지 못하면 경고
        if matched_count > len(old_feed_list) / 2:
            sorted_feed_list: List[Dict[str, Any]] = sorted(feed_id_sort_field_list, key=self._cmp_to_key(self._cmp_int_or_str))
        else:
            LOGGER.warning(f"Warning: can't match the pattern /{self.collection_conf['sort_field_pattern']}/")
            sorted_feed_list = feed_id_sort_field_list

        start_idx, end_idx, mtime = self._get_idx_data()
        if not mtime:
            LOGGER.error("ERROR: can't read start_idx.txt file")
            return None
        LOGGER.info(f"start index: {start_idx}, end index: {end_idx}, last modified time: {mtime}")
        result_feed_list: List[Tuple[str, str]] = []
        for i, feed in enumerate(sorted_feed_list):
            feed_id = feed["id"]
            if start_idx <= i + 1 < end_idx:
                # link, title = old_feed_list[feed_id]
                result_feed_list.append(old_feed_list[feed_id])

        next_start_idx, current_time_str = self._write_idx_data(start_idx, mtime)
        if current_time_str:
            LOGGER.info(f"next start index: {next_start_idx}, current time: {current_time_str}")
        return result_feed_list

    def _get_recent_feed_list(self) -> List[Tuple[str, str]]:
        LOGGER.debug("# _get_recent_feed_list()")

        short_date_str = Datetime.get_short_date_str()
        new_list_file_path = FeedMaker._get_list_file_path(self.list_dir, short_date_str)
        collector = NewListCollector(self.feed_dir_path, self.collection_conf, new_list_file_path)
        return collector.collect()

    def _diff_feeds_and_make_htmls(self, recent_feed_list: List[Tuple[str, str]], old_feed_list: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        LOGGER.debug(f"# _diff_feeds_and_make_htmls(recent_feed_list={recent_feed_list}, old_feed_list={old_feed_list})")

        recent_set = OrderedSet(recent_feed_list)
        old_set = OrderedSet(old_feed_list)
        new_feed_list = list(recent_set - old_set)

        # collect items to be generated as RSS feed
        LOGGER.info(f"Appending {len(new_feed_list)} new items to the feed list")
        merged_feed_list: List[Tuple[str, str]] = []
        for link, title in new_feed_list:
            if self._make_html_file(link, title):
                merged_feed_list.append((link, title))

        LOGGER.info(f"Appending {len(old_feed_list)} old items to the feed list")
        for link, title in old_feed_list:
            if self._make_html_file(link, title):
                merged_feed_list.append((link, title))
        return merged_feed_list[:self.window_size]

    def _generate_rss_feed(self, merged_feed_list: List[Tuple[str, str]]) -> bool:
        LOGGER.debug("# generate_rss_feed()")

        if not self.rss_conf:
            LOGGER.error("ERROR: can't get rss configuration")
            return False

        last_build_date_str = Datetime.get_rss_date_str()
        short_date_str = Datetime.get_short_date_str()
        temp_rss_file_path = self.rss_file_path.with_suffix("." + short_date_str)
        old_rss_file_path = self.rss_file_path.with_suffix(self.rss_file_path.suffix + ".old")
        LOGGER.debug(f"rss_file_path={self.rss_file_path}, temp_rss_file_path={temp_rss_file_path}, old_rss_file_path={old_rss_file_path}")

        LOGGER.info("Generating rss feed file...")
        rss_items: List[PyRSS2Gen.RSSItem] = []
        for link, title in reversed(merged_feed_list):
            html_file_path = FeedMaker._get_html_file_path(self.html_dir, link)
            LOGGER.info(f"{link}\t{title}\t{PathUtil.convert_path_to_str(html_file_path)}")
            pub_date_str = Datetime.get_rss_date_str()

            content = ""
            with html_file_path.open("r", encoding="utf-8") as in_file:
                for line in in_file:
                    content += line
                    # restrict big contents
                    if len(content) >= self.MAX_CONTENT_LENGTH:
                        content = "<strong>본문이 너무 길어서 전문을 싣지 않았습니다. 다음의 원문 URL을 참고해주세요.</strong><br/>" + content
                        break

            if self.rss_conf["rss_url_prefix_for_guid"]:
                guid = self.rss_conf["rss_url_prefix_for_guid"] + URL.get_url_path(link)
            else:
                guid = link
            rss_items.append(
                PyRSS2Gen.RSSItem(
                    title=title,
                    link=link,
                    guid=guid,
                    pubDate=pub_date_str,
                    description=content
                )
            )

        rss = PyRSS2Gen.RSS2(
            title=self.rss_conf["rss_title"],
            link=self.rss_conf["rss_link"],
            description=self.rss_conf["rss_description"],
            lastBuildDate=last_build_date_str,
            items=rss_items
        )
        with temp_rss_file_path.open('w', encoding="utf-8") as outfile:
            rss.write_xml(outfile, encoding='utf-8')

        # 이번에 만들어진 rss 파일이 이전 파일과 내용이 다른지 확인
        is_different = False
        if self.rss_file_path.is_file():
            if not Data.compare_two_rss_files(self.rss_file_path, temp_rss_file_path):
                is_different = True
        else:
            is_different = True

        LOGGER.debug(f"is_differernt={is_different}")
        if is_different:
            # 이전 파일을 old 파일로 이름 바꾸기
            if self.rss_file_path.is_file():
                LOGGER.debug(f"renaming '{self.rss_file_path}' to '{old_rss_file_path}'")
                self.rss_file_path.rename(old_rss_file_path)
            # 이번에 만들어진 파일을 정식 파일 이름으로 바꾸기
            if temp_rss_file_path.is_file():
                LOGGER.debug(f"renaming '{temp_rss_file_path}' to '{self.rss_file_path}'")
                temp_rss_file_path.rename(self.rss_file_path)
        else:
            # 이번에 만들어진 파일을 지우기
            temp_rss_file_path.unlink(missing_ok=True)

        return True

    def make(self) -> bool:
        LOGGER.debug("# make()")
        LOGGER.info("=========================================================")
        LOGGER.info(f"{PathUtil.convert_path_to_str(self.feed_dir_path)} ")
        LOGGER.info("=========================================================")

        config = Config(feed_dir_path=self.feed_dir_path)
        if not config:
            LOGGER.error("Error: Can't get configuration")
            sys.exit(-1)
        self.collection_conf = config.get_collection_configs()
        if not self.collection_conf:
            LOGGER.error("Error: Can't get collection configuration")
            return False
        self.extraction_conf = config.get_extraction_configs()
        if not self.extraction_conf:
            LOGGER.error("Error: Can't get extraction configuration")
            return False
        self.rss_conf = config.get_rss_configs()
        if not self.rss_conf:
            LOGGER.error("Error: Can't get rss configuration")
            return False
        LOGGER.debug(f"self.collection_conf={self.collection_conf}")
        LOGGER.debug(f"self.extraction_conf={self.extraction_conf}")
        LOGGER.debug(f"self.rss_conf={self.rss_conf}")

        # window_size (get value from configuration in case unspecified manually by run.py)
        if self.window_size == FeedMaker.DEFAULT_WINDOW_SIZE:
            if self.collection_conf["window_size"] > 0:
                self.window_size = self.collection_conf["window_size"]

        # -c 또는 -l 옵션이 지정된 경우, 설정의 is_completed 값 무시
        if self.do_collect_by_force or self.do_collect_only:
            self.collection_conf["is_completed"] = False

        old_feed_list: List[Tuple[str, str]] = []
        if not self.do_collect_only:
            # 과거 피드항목 리스트를 가져옴
            old_feed_list = self._read_old_feed_list_from_file()
            if not old_feed_list:
                LOGGER.warning("Warning: can't read old feed list from files")

        # 완결여부 설정값 판단
        if self.collection_conf["is_completed"]:
            # 완결된 피드는 적재된 리스트에서 일부 피드항목을 꺼내옴
            final_feed_list = self._fetch_old_feed_list_window(old_feed_list)
            if not final_feed_list:
                LOGGER.error("Error: can't get collection configuration")
                return False
        else:
            # 피딩 중인 피드는 최신 피드항목을 받아옴
            recent_feed_list = self._get_recent_feed_list()
            if not recent_feed_list:
                LOGGER.error("Error: Can't get recent feed list from urls")
                return False

            if self.collection_conf["ignore_old_list"]:
                old_feed_list.clear()
                # new_feed_list = recent_feed_list

            # 과거 피드항목 리스트와 최근 피드항목 리스트를 비교함
            final_feed_list = self._diff_feeds_and_make_htmls(recent_feed_list, old_feed_list)
            if not final_feed_list or len(final_feed_list) == 0:
                LOGGER.info("No new feeds, no update of rss file")

        if not self.do_collect_by_force:
            # generate RSS feed
            if not self._generate_rss_feed(final_feed_list):
                return False

            # upload RSS feed file
            Uploader.upload(self.rss_file_path)

        return True
