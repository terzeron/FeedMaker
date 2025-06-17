#!/usr/bin/env python


import json
import math
import logging.config
from pathlib import Path
from datetime import datetime, timedelta, timezone
from itertools import islice
from typing import Any, Optional
from bin.feed_maker_util import PathUtil, Env
from bin.db import DB, Session
from bin.models import FeedInfo, ElementNameCount

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class FeedManager:
    work_dir_path = Path(Env.get("FM_WORK_DIR"))
    public_feed_dir_path = Path(Env.get("WEB_SERVICE_FEED_DIR_PREFIX"))
    
    @classmethod
    def get_feed_name_list_url_count_map(cls) -> dict[str, dict[str, Any]]:
        LOGGER.debug("# get_feed_name_list_url_count_map()")
        feed_name_list_url_count_map: dict[str, dict[str, Any]] = {}

        with DB.session_ctx() as s:
            rows = s.query(FeedInfo).filter(FeedInfo.url_list_count > 1).all()
            for row in rows:
                feed_name: str = row.feed_name
                feed_name_list_url_count_map[feed_name] = {
                    "feed_name": feed_name,
                    "feed_title": row.feed_title,
                    "group_name": row.group_name,
                    "count": row.url_list_count
                }

        return feed_name_list_url_count_map

    @classmethod
    def get_element_name_count_map(cls) -> dict[str, dict[str, Any]]:
        LOGGER.debug("# get_element_name_count_map()")
        element_name_count_map: dict[str, dict[str, Any]] = {}

        with DB.session_ctx() as s:
            for row in s.query(ElementNameCount).all():
                element_name = row.element_name
                element_name_count_map[element_name] = {
                    "element_name": element_name,
                    "count": row.count
                }

        return element_name_count_map

    @classmethod
    def remove_config_info(cls, feed_dir_path: Path, do_remove_file: bool = False) -> None:
        LOGGER.debug("# remove_config_info(feed_dir_path='%s', do_remove_file=%r)", PathUtil.short_path(feed_dir_path), do_remove_file)
        feed_name = feed_dir_path.name
        if do_remove_file:
            (feed_dir_path / "conf.json").unlink(missing_ok=True)
        with DB.session_ctx() as s:
            s.query(FeedInfo).filter_by(feed_name=feed_name).update({
                FeedInfo.is_active: False,
                FeedInfo.config: "",
                FeedInfo.config_modify_date: None
            })
        LOGGER.info("* The removing of config info of feed '%s' is done.", feed_name)

    @classmethod
    def _add_config_info(cls, s: Session, feed_dir_path: Path, element_name_count_map: Optional[dict[str, int]] = None) -> None:
        if not feed_dir_path.is_dir():
            LOGGER.error("can't find a feed directory '%s'", PathUtil.short_path(feed_dir_path))
            return
        element_name_count_map = element_name_count_map if element_name_count_map is not None else {}
        feed_name = feed_dir_path.name
        group_name = feed_dir_path.parent.name

        title: str = ""
        config_str: str = ""
        url_list_count: int = 0
        is_completed: bool = False
        unit_size_per_day: float = 0.0
        config_modify_date: datetime = datetime.now(timezone.utc)

        if group_name in (".mypy_cache", ".git", "test") or feed_name in (".mypy_cache", ".git", "test"):
            return
        if group_name.startswith("_") or feed_name.startswith("_"):
            # disabled feed
            is_active = False
            if group_name.startswith("_"):
                group_name = group_name[1:]
            if feed_name.startswith("_"):
                feed_name = feed_name[1:]
        else:
            # active feed
            is_active = True
            conf_json_file_path = feed_dir_path / "conf.json"
            if feed_dir_path.is_dir() and conf_json_file_path.is_file():
                st = feed_dir_path.stat()
                config_modify_date = datetime.fromtimestamp(st.st_mtime, timezone.utc)

                with conf_json_file_path.open("r", encoding="utf-8") as infile:
                    json_data = json.load(infile)
                configuration: dict[str, dict[str, Any]] = {}
                if json_data:
                    configuration = json_data.get("configuration", {})
                    if configuration:
                        config_str = json.dumps(configuration)
                        rss_data = configuration.get("rss", {})
                        title = rss_data.get("title", "")
                        if "::" in title:
                            title = title.split("::")[0]
                        collection_data = configuration.get("collection", {})
                        url_list_count = len(collection_data.get("list_url_list", []))
                        is_completed = collection_data.get("is_completed", False)
                        unit_size_per_day = collection_data.get("unit_size_per_day", 0)

                for sub_config_element in ["collection", "extraction", "rss"]:
                    for element in configuration.get(sub_config_element, {}):
                        key = sub_config_element[0] + "." + element
                        element_name_count_map[key] = element_name_count_map.get(key, 0) + 1

        existing_feed = s.query(FeedInfo).filter_by(feed_name=feed_name, group_name=group_name).first()
        if existing_feed:
            existing_feed.feed_title = title
            existing_feed.is_active = is_active
            existing_feed.config = config_str
            existing_feed.config_modify_date = config_modify_date
            existing_feed.url_list_count = url_list_count
            existing_feed.is_completed = is_completed
            existing_feed.unit_size_per_day = unit_size_per_day
        else:
            s.add(FeedInfo(feed_name=feed_name, group_name=group_name, feed_title=title, is_active=is_active, config=config_str, config_modify_date=config_modify_date, url_list_count=url_list_count, is_completed=is_completed, unit_size_per_day=unit_size_per_day))
        
        s.flush()

    @classmethod
    def add_config_info(cls, feed_dir_path: Path) -> None:
        feed_name = feed_dir_path.name
        with DB.session_ctx() as s:
            element_name_count_map: dict[str, int] = {}
            FeedManager._add_config_info(s, feed_dir_path, element_name_count_map)
            FeedManager._add_element_info(element_name_count_map)
        LOGGER.info("* The adding of config info of feed '%s' is done.", feed_name)

    @classmethod
    def _add_element_info(cls, element_name_count_map: dict[str, int], total_element_name_count_map: Optional[dict[str, int]] = None) -> None:
        if total_element_name_count_map is not None:
            for element_name, count in element_name_count_map.items():
                total_element_name_count_map[element_name] = total_element_name_count_map.get(element_name, 0) + count

    def load_all_config_files(self, max_num_feeds: Optional[int] = None) -> None:
        LOGGER.debug("# load_all_config_files(max_num_feeds=%r)", max_num_feeds)
        start_ts = datetime.now(timezone.utc)
        
        with DB.session_ctx() as s:
            num_items = 0
            element_name_count_map: dict[str, int] = {}
            total_element_name_count_map: dict[str, int] = {}
            for group_dir_path in islice(self.work_dir_path.iterdir(), max_num_feeds):
                if not group_dir_path.is_dir():
                    continue

                for feed_dir_path in group_dir_path.iterdir():
                    if not feed_dir_path.is_dir():
                        continue
                    FeedManager._add_config_info(s, feed_dir_path, element_name_count_map)
                    FeedManager._add_element_info(element_name_count_map, total_element_name_count_map)
                    num_items += 1

            for element_name, count in total_element_name_count_map.items():
                s.merge(ElementNameCount(element_name=element_name, count=count))
                
        end_ts = datetime.now(timezone.utc)
        LOGGER.info("* The loading of all config files is done. %d items / %s sec", num_items, (end_ts - start_ts))

    @classmethod
    def remove_rss_info(cls, feed_dir_path: Path, do_remove_file: bool = False) -> None:
        LOGGER.debug("# remove_rss_info(feed_dir_path='%s', do_remove_file=%r)", PathUtil.short_path(feed_dir_path), do_remove_file)
        feed_name = feed_dir_path.name
        if do_remove_file:
            (feed_dir_path / f"{feed_name}.xml").unlink(missing_ok=True)
        with DB.session_ctx() as s:
            s.query(FeedInfo).filter_by(feed_name=feed_name).update({
                FeedInfo.feedmaker: False,
                FeedInfo.rss_update_date: None
            })
        LOGGER.info("* The removing of rss info of feed '%s' is done.", feed_name)

    @classmethod
    def _add_rss_info(cls, s: Session, feed_dir_path: Path) -> None:
        if not feed_dir_path.is_dir():
            LOGGER.error("can't find a feed directory '%s'", PathUtil.short_path(feed_dir_path))
            return
        feed_name = feed_dir_path.name
        group_name = feed_dir_path.parent.name

        feedmaker = False
        rss_update_date: Optional[datetime] = None

        if group_name in (".mypy_cache", ".git", "test") or feed_name in (".mypy_cache", ".git", "test"):
            return
        if group_name.startswith("_") or feed_name.startswith("_"):
            # disabled feed
            is_active = False
            if group_name.startswith("_"):
                group_name = group_name[1:]
            if feed_name.startswith("_"):
                feed_name = feed_name[1:]
        else:
            # active feed
            is_active = True
            rss_file_path = feed_dir_path / f"{feed_name}.xml"
            if rss_file_path.is_file():
                feedmaker = True
                st = rss_file_path.stat()
                rss_update_date = datetime.fromtimestamp(st.st_mtime, timezone.utc)

        existing_feeds = s.query(FeedInfo).filter_by(feed_name=feed_name, is_active=is_active).all()
        if existing_feeds:
            for feed in existing_feeds:
                feed.feedmaker = feedmaker
                feed.rss_update_date = rss_update_date
        else:
            s.add(FeedInfo(feed_name=feed_name, group_name=group_name, feedmaker=feedmaker, rss_update_date=rss_update_date))

    @classmethod
    def add_rss_info(cls, feed_dir_path: Path) -> None:
        feed_name = feed_dir_path.name
        with DB.session_ctx() as s:
            FeedManager._add_rss_info(s, feed_dir_path)
        LOGGER.info("* The adding of rss info of feed '%s' is done.", feed_name)

    def load_all_rss_files(self, max_num_feeds: Optional[int] = None) -> None:
        LOGGER.debug("# load_all_rss_files(max_num_feeds=%r)", max_num_feeds)
        start_ts = datetime.now(timezone.utc)
        
        with DB.session_ctx() as s:
            num_items = 0
            for group_dir_path in islice(self.work_dir_path.iterdir(), max_num_feeds):
                if not group_dir_path.is_dir():
                    continue

                for feed_dir_path in group_dir_path.iterdir():
                    if not feed_dir_path.is_dir():
                        continue
                    FeedManager._add_rss_info(s, feed_dir_path)
                    num_items += 1
            
        end_ts = datetime.now(timezone.utc)
        LOGGER.info("* The loading of all rss files is done. %d items / %s sec", num_items, (end_ts - start_ts))

    @classmethod
    def get_feed_name_public_feed_info_map(cls) -> dict[str, dict[str, Any]]:
        LOGGER.debug("# get_feed_name_public_feed_info_map()")
        feed_name_public_feed_info_map: dict[str, dict[str, Any]] = {}

        with DB.session_ctx() as s:
            rows = s.query(FeedInfo).where(FeedInfo.public_html).all()
            for row in rows:
                feed_name = row.feed_name
                feed_name_public_feed_info_map[feed_name] = {
                    "feed_name": feed_name,
                    "feed_title": row.feed_title,
                    "group_name": row.group_name,
                    "file_size": row.file_size,
                    "num_items": row.num_items,
                    "upload_date": row.upload_date
                }

        return feed_name_public_feed_info_map

    @classmethod
    def remove_public_feed(cls, public_feed_file_path: Path, do_remove_file: bool = False) -> None:
        feed_name = public_feed_file_path.stem
        if do_remove_file:
            public_feed_file_path.unlink(missing_ok=True)
        with DB.session_ctx() as s:
            s.query(FeedInfo).filter_by(feed_name=feed_name).update({
                FeedInfo.public_html: False,
                FeedInfo.public_feed_file_path: "",
                FeedInfo.file_size: 0,
                FeedInfo.num_items: 0,
                FeedInfo.upload_date: None
            })
            LOGGER.info("* The removing of public feed info of feed '%s' is done.", feed_name)

    def remove_public_feed_by_feed_name(self, feed_name: str, do_remove_file: bool = False) -> None:
        public_feed_file_path = self.public_feed_dir_path / f"{feed_name}.xml"
        FeedManager.remove_public_feed(public_feed_file_path, do_remove_file=do_remove_file)

    @classmethod
    def _add_public_feed(cls, s: Session, public_feed_file_path: Path) -> int:
        if not public_feed_file_path.is_file():
            LOGGER.error("can't find a public feed file '%s'", PathUtil.short_path(public_feed_file_path))
            return 0

        feed_name = public_feed_file_path.stem
        st = public_feed_file_path.stat()
        file_size = st.st_size
        upload_date = datetime.fromtimestamp(st.st_mtime, timezone.utc)

        with public_feed_file_path.open("r", encoding="utf-8") as infile:
            file_content = infile.read()
        num_items = file_content.count("<item>")

        existing_feeds = s.query(FeedInfo).filter_by(feed_name=feed_name).all()
        if existing_feeds:
            for feed in existing_feeds:
                feed.public_html = True
                feed.public_feed_file_path = str(public_feed_file_path)
                feed.file_size = file_size
                feed.num_items = num_items
                feed.upload_date = upload_date
        else:
            s.add(FeedInfo(
                feed_name=feed_name, 
                public_html=True, 
                public_feed_file_path=str(public_feed_file_path), 
                file_size=file_size, 
                num_items=num_items, 
                upload_date=upload_date
            ))

        return num_items

    @classmethod
    def add_public_feed(cls, public_feed_file_path: Path) -> None:
        feed_name = public_feed_file_path.stem
        with DB.session_ctx() as s:
            num_items = FeedManager._add_public_feed(s, public_feed_file_path)
        LOGGER.info("* The adding of public feed info of feed '%s' is done. %d items", feed_name, num_items)

    def add_public_feed_by_feed_name(self, feed_name: str) -> None:
        public_feed_file_path = self.public_feed_dir_path / f"{feed_name}.xml"
        FeedManager.add_public_feed(public_feed_file_path)

    def load_all_public_feed_files(self, max_num_public_feeds: Optional[int] = None) -> None:
        LOGGER.debug("# load_all_public_feed_files(max_num_public_feeds=%r)", max_num_public_feeds)
        start_ts = datetime.now(timezone.utc)
        
        with DB.session_ctx() as s:
            num_items = 0
            for public_feed_file_path in islice(self.public_feed_dir_path.glob("*.xml"), max_num_public_feeds):
                num_items += FeedManager._add_public_feed(s, public_feed_file_path)
            
        end_ts = datetime.now(timezone.utc)
        LOGGER.info("* The loading of all public feed files is done. %d items / %s sec", num_items, (end_ts - start_ts))

    @classmethod
    def get_feed_name_progress_info_map(cls) -> dict[str, dict[str, Any]]:
        LOGGER.debug("# get_feed_name_progress_info_map()")
        feed_name_progress_info_map: dict[str, dict[str, Any]] = {}

        with DB.session_ctx() as s:
            rows = s.query(FeedInfo).where(FeedInfo.is_completed).all()
            for row in rows:
                feed_name = row.feed_name
                unit_size_per_day: float = row.unit_size_per_day or 0.0
                progress_ratio: float = row.progress_ratio or 0.0
                feed_name_progress_info_map[feed_name] = {
                    "feed_name": feed_name,
                    "feed_title": row.feed_title,
                    "group_name": row.group_name,
                    "current_index": row.current_index,
                    "total_item_count": row.total_item_count,
                    "unit_size_per_day": unit_size_per_day,
                    "progress_ratio": progress_ratio,
                    "due_date": row.due_date
                }

        return feed_name_progress_info_map

    @classmethod
    def remove_progress_info(cls, feed_dir_path: Path, do_remove_file: bool = False) -> None:
        LOGGER.debug("# remove_progress_info(feed_dir_path='%s', do_remove_file=%r)", PathUtil.short_path(feed_dir_path), do_remove_file)
        feed_name = feed_dir_path.name
        if do_remove_file:
            (feed_dir_path / "start_idx.txt").unlink(missing_ok=True)
        with DB.session_ctx() as s:
            s.query(FeedInfo).filter_by(feed_name=feed_name).update({
                FeedInfo.is_completed: False,
                FeedInfo.current_index: 0,
                FeedInfo.total_item_count: 0,
                FeedInfo.unit_size_per_day: 0,
                FeedInfo.progress_ratio: 0.0,
                FeedInfo.due_date: None
            })
        LOGGER.info("* The removing of progress info of feed '%s' is done.", feed_name)

    @classmethod
    def _add_progress_info(cls, s: Session, feed_dir_path: Path) -> int:
        if not feed_dir_path.is_dir():
            LOGGER.error("can't find a feed directory '%s'", PathUtil.short_path(feed_dir_path))
            return 0

        feed_name = feed_dir_path.name
        group_name = feed_dir_path.parent.name

        is_completed: bool = False
        current_index: int = 0
        total_item_count: int = 0
        progress_ratio: float = 0.0
        due_date: Optional[datetime] = None
        collect_date: Optional[datetime] = None

        if group_name in (".mypy_cache", ".git", "test") or feed_name in (".mypy_cache", ".git", "test"):
            return 0
        
        if group_name.startswith("_") or feed_name.startswith("_"):
            # disabled feed
            is_active = False
            if group_name.startswith("_"):
                group_name = group_name[1:]
            if feed_name.startswith("_"):
                feed_name = feed_name[1:]
        else:
            # active feed
            is_active = True
       
        row = s.query(FeedInfo).where(FeedInfo.feed_name == feed_name, FeedInfo.is_completed).first()
        if row is not None:
            unit_size_per_day = row.unit_size_per_day
            is_completed = True
            # read current_index from start_idx.txt
            current_index = 0
            file_path = feed_dir_path / "start_idx.txt"
            if file_path.is_file():
                with file_path.open('r', encoding="utf-8") as infile:
                    line = infile.readline()
                current_index = int(line.split('\t')[0])

            # determine total_item_count & collect_date
            url_list: list[str] = []
            list_dir_path = feed_dir_path / "newlist"
            collect_date = None
            if list_dir_path.is_dir():
                for list_file_path in list_dir_path.iterdir():
                    if list_file_path.suffix == ".txt":
                        st = list_file_path.stat()
                        temp_dt = datetime.fromtimestamp(st.st_mtime, timezone.utc)
                        if not collect_date or collect_date < temp_dt:
                            collect_date = temp_dt
                        with list_file_path.open('r', encoding="utf-8") as infile:
                            for line in infile:
                                url = line.split('\t')[0]
                                url_list.append(url)
            total_item_count = len(list(set(url_list)))

            # progress information
            progress_ratio = int((current_index + 4) * 100 / (total_item_count + 1))
            remainder = total_item_count - (current_index + 4)
            num_days = int(math.ceil(remainder / unit_size_per_day))
            due_date = datetime.now(timezone.utc) + timedelta(days=num_days)

        # feed_name만으로 검색 (기본키가 feed_name이므로)
        existing_feeds = s.query(FeedInfo).filter_by(feed_name=feed_name, group_name=group_name).all()
        if existing_feeds:
            for feed in existing_feeds:
                feed.is_completed = is_completed
                feed.current_index = current_index
                feed.total_item_count = total_item_count
                feed.progress_ratio = progress_ratio
                feed.due_date = due_date
                feed.collect_date = collect_date
        else:
            s.add(FeedInfo(feed_name=feed_name, group_name=group_name, is_active=is_active, is_completed=is_completed, current_index=current_index, total_item_count=total_item_count, progress_ratio=progress_ratio, due_date=due_date, collect_date=collect_date))
        
        return 1

    @classmethod
    def add_progress_info(cls, feed_dir_path: Path) -> None:
        feed_name = feed_dir_path.name
        with DB.session_ctx() as s:
            num_items = FeedManager._add_progress_info(s, feed_dir_path)
        LOGGER.info("* The adding of progress info of feed '%s' is done. %d items", feed_name, num_items)

    def load_all_progress_info_from_files(self, max_num_feeds: Optional[int] = None) -> None:
        LOGGER.debug("# load_all_progress_info_from_files(max_num_feeds=%r)", max_num_feeds)
        start_ts = datetime.now(timezone.utc)
        
        with DB.session_ctx() as s:
            num_items = 0
            for group_dir_path in islice(self.work_dir_path.iterdir(), max_num_feeds):
                if not group_dir_path.is_dir():
                    continue

                for feed_dir_path in group_dir_path.iterdir():
                    if not feed_dir_path.is_dir():
                        continue
                    num_items += FeedManager._add_progress_info(s, feed_dir_path)
            
        end_ts = datetime.now(timezone.utc)
        LOGGER.info("* The loading of all progress info from files is done. %d items / %s sec", num_items, (end_ts - start_ts))

    @classmethod
    def search(cls, keywords: list[str]) -> list[dict[str, Any]]:
        if not keywords:
            return []

        results: list[dict[str, Any]] = []
        with DB.session_ctx() as s:
            for keyword in keywords:
                escaped = keyword.replace('%', r'\%').replace('_', r'\_')
                pat = f"%{escaped}%"
                rows = s.query(FeedInfo).where((FeedInfo.feed_name.like(pat, escape='\\') |
                                                FeedInfo.feed_title.like(pat, escape='\\') |
                                                FeedInfo.group_name.like(pat, escape='\\')) &
                                               FeedInfo.feedmaker).order_by(FeedInfo.group_name, FeedInfo.feed_name).all()
                results.extend([{"feed_name": row.feed_name, "feed_title": row.feed_title, "group_name": row.group_name} for row in rows])
        return results

    @classmethod
    def get_groups(cls) -> list[dict[str, Any]]:
        LOGGER.debug("# get_groups()")

        with DB.session_ctx() as s:
            # 모든 그룹 이름을 가져와서 중복 제거
            group_names = [row.group_name for row in s.query(FeedInfo.group_name).where(FeedInfo.group_name != "").distinct().all()]
            result: list[dict[str, Any]] = []
            for group_name in sorted(group_names):
                # 각 그룹별 피드 수 계산
                count = s.query(FeedInfo).filter_by(group_name=group_name).count()
                result.append({"name": group_name, "num_feeds": count})
            return result

    @classmethod
    def get_feeds_by_group(cls, group_name: str) -> list[dict[str, Any]]:
        LOGGER.debug("# get_feeds_by_group(group_name='%s')", group_name)

        with DB.session_ctx() as s:
            rows = s.query(FeedInfo).where(FeedInfo.group_name == group_name).order_by(FeedInfo.feed_name).all()
            return [{"name": row.feed_name, "title": row.feed_title if row.feed_title else row.feed_name, "group_name": row.group_name} for row in rows]

    @classmethod
    def get_feed_info(cls, group_name: str, feed_name: str) -> dict[str, Any]:
        LOGGER.debug("# get_feed_info(group_name='%s', feed_name='%s')", group_name, feed_name)

        with DB.session_ctx() as s:
            feed = s.query(FeedInfo).where(FeedInfo.feed_name == feed_name, 
                                           FeedInfo.group_name == group_name,                                    
                                           FeedInfo.config.isnot(None)).first()

        if not feed:
            return {}

        return {
            "feed_name": feed.feed_name,
            "feed_title": feed.feed_title,
            "group_name": feed.group_name,
            "config": json.loads(str(feed.config)),
            "config_modify_date": feed.config_modify_date,
            "collection_info": {
                "collect_date": feed.collect_date,
                "total_item_count": feed.total_item_count,
            },
            "public_feed_info": {
                "public_feed_file_path": feed.public_feed_file_path,
                "file_size": feed.file_size,
                "num_items": feed.num_items,
                "upload_date": feed.upload_date,
            },
            "progress_info": {
                "current_index": feed.current_index,
                "total_item_count": feed.total_item_count,
                "unit_size_per_day": feed.unit_size_per_day,
                "progress_ratio": feed.progress_ratio,
                "due_date": feed.due_date,
            },
        }

    @classmethod
    def toggle_feed(cls, feed_name: str) -> bool:
        LOGGER.debug("# toggle_feed(feed_name='%s')", feed_name)
        with DB.session_ctx() as s:
            row = s.query(FeedInfo).where(FeedInfo.feed_name == feed_name).first()
            if row:
                feed_name_str = row.feed_name
                if feed_name_str.startswith("_"):
                    new_feed_name = feed_name_str[1:]
                    is_active = True
                else:
                    new_feed_name = "_" + feed_name_str
                    is_active = False
                s.query(FeedInfo).filter_by(feed_name=feed_name).update({
                    FeedInfo.feed_name: new_feed_name,
                    FeedInfo.is_active: is_active
                })
        return True

    @classmethod
    def toggle_group(cls, group_name: str) -> bool:
        LOGGER.debug("# toggle_group(group_name='%s')", group_name)
        with DB.session_ctx() as s:
            row = s.query(FeedInfo).where(FeedInfo.group_name == group_name).first()
            if row:
                group_name_str = row.group_name
                if group_name_str.startswith("_"):
                    new_group_name = group_name_str[1:]
                    is_active = True
                else:
                    new_group_name = "_" + group_name_str
                    is_active = False
                s.query(FeedInfo).filter_by(group_name=group_name).update({
                    FeedInfo.group_name: new_group_name,
                    FeedInfo.is_active: is_active
                })
        return True

    def load_all(self, max_num_feeds: Optional[int] = None, max_num_public_feeds: Optional[int] = None) -> None:
        LOGGER.debug("* start loading information")
        self.load_all_config_files(max_num_feeds)
        self.load_all_rss_files(max_num_feeds)
        self.load_all_public_feed_files(max_num_public_feeds)
        self.load_all_progress_info_from_files(max_num_feeds)
        LOGGER.debug("* finish loading information")
