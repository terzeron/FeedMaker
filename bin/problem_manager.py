#!/usr/bin/env python


import os
import logging.config
from pathlib import Path
from typing import Any, Optional, TypedDict
from bin.feed_maker_util import PathUtil, Env
from bin.feed_manager import FeedManager
from bin.access_log_manager import AccessLogManager
from bin.html_file_manager import HtmlFileManager
from bin.db import DB, not_, and_, or_, func
from bin.models import FeedInfo

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class FeedImageDirSizeInfo(TypedDict):
    feed_name: str
    feed_title: str
    group_name: str
    size: int


class ProblemManager:
    num_days = 60
    is_tables_created = False
    # 이미지 디렉터리 크기 추정 시 stat할 최대 표본 파일 수
    image_dir_size_sample_count = 200

    def __init__(self) -> None:
        if not ProblemManager.is_tables_created:
            DB.create_all_tables()
            ProblemManager.is_tables_created = True
        self.feed_manager = FeedManager()
        self.html_file_manager = HtmlFileManager()

    def __del__(self) -> None:
        del self.feed_manager
        del self.html_file_manager

    @classmethod
    def get_feed_name_status_info_map(cls) -> dict[str, dict[str, Any]]:
        LOGGER.debug("# get_feed_name_status_info_map()")
        feed_name_status_info_map: dict[str, dict[str, Any]] = {}

        # exclude feeds unrequested and unregistered and unmade
        # --> NOT ( http_request = 0 AND public_html = 0 AND feedmaker = 0 )
        # exclude feeds REQUESTED and unregistered and unmade but ACCESSED long ago
        # --> NOT ( http_request = 1 AND public_html = 0 AND feedmaker = 0 AND access_date IS NOT NULL AND DATEDIFF(current_date, access_date) > %s )
        # exclude feeds REQUESTED and REGISTERED and MADE AND ACCESSED OR VIEWED RECENTLY
        # --> NOT ( http_request = 1 AND public_html = 1 AND feedmaker = 1 AND ( access_date IS NOT NULL AND DATEDIFF(current_date, access_date) < %s OR view_date IS NOT NULL AND DATEDIFF(current_date, view_date) < %s ) )
        # for row in self.db.query("SELECT * FROM feed_info WHERE NOT ( http_request = 0 AND public_html = 0 AND feedmaker = 0 ) AND NOT ( http_request = 1 AND public_html = 0 AND feedmaker = 0 AND access_date IS NOT NULL AND DATEDIFF(current_date, access_date) > %s ) AND NOT ( http_request = 1 AND public_html = 1 AND feedmaker = 1 AND config IS NOT NULL AND ( access_date IS NOT NULL AND DATEDIFF(current_date, access_date) < %s OR view_date IS NOT NULL AND DATEDIFF(current_date, view_date) < %s ) ) ORDER BY feedmaker, public_html, http_request, collect_date, rss_update_date, upload_date, access_date, view_date", self.num_days, self.num_days, self.num_days):
        with DB.session_ctx() as s:
            rows = (
                s.query(FeedInfo)
                .where(
                    # 비활성화된 피드 제외
                    FeedInfo.is_active,
                    # 1) http_request=0 AND public_html=0 AND feedmaker=0 AND config="" 인 행 제외
                    #    (설정이 있는 미운영 피드는 문제로 표시)
                    not_(and_(not_(FeedInfo.http_request), not_(FeedInfo.public_html), not_(FeedInfo.feedmaker), FeedInfo.config == "")),
                    # 2) http_request=1, public_html=0, feedmaker=0, access_date IS NOT NULL,
                    #    DATEDIFF(current_date, access_date) > num_days 인 행 제외
                    not_(and_(FeedInfo.http_request, not_(FeedInfo.public_html), not_(FeedInfo.feedmaker), FeedInfo.access_date.isnot(None), func.datediff(func.current_date(), FeedInfo.access_date) > cls.num_days)),
                    # 3) http_request=1, public_html=1, feedmaker=1, config IS NOT NULL,
                    #    AND (access_date IS NOT NULL AND DATEDIFF(current_date,access_date)<num_days
                    #         OR view_date IS NOT NULL AND DATEDIFF(current_date,view_date)<num_days)
                    # 3) http_request=1, public_html=1, feedmaker=1, config 비어있지 않음,
                    #    AND (access_date IS NOT NULL AND DATEDIFF(current_date,access_date)<num_days
                    #         OR view_date IS NOT NULL AND DATEDIFF(current_date,view_date)<num_days)
                    not_(
                        and_(
                            FeedInfo.http_request,
                            FeedInfo.public_html,
                            FeedInfo.feedmaker,
                            FeedInfo.config != "",
                            or_(and_(FeedInfo.access_date.isnot(None), func.datediff(func.current_date(), FeedInfo.access_date) < cls.num_days), and_(FeedInfo.view_date.isnot(None), func.datediff(func.current_date(), FeedInfo.view_date) < cls.num_days)),
                        )
                    ),
                )
                .order_by(FeedInfo.feedmaker, FeedInfo.public_html, FeedInfo.http_request, FeedInfo.collect_date, FeedInfo.rss_update_date, FeedInfo.upload_date, FeedInfo.access_date, FeedInfo.view_date)
                .all()
            )
            # 전체 테이블에서 feedmaker=True인 feed_name 수집 (필터링된 rows가 아닌 원본)
            feedmaker_true_names: set[str] = {r.feed_name for r in s.query(FeedInfo.feed_name).filter(FeedInfo.feedmaker).all()}

            for row in rows:
                feed_name = row.feed_name
                # feedmaker=False인데 같은 이름으로 feedmaker=True가 존재하면 건너뜀
                if not row.feedmaker and feed_name in feedmaker_true_names:
                    continue
                feed_name_status_info_map[feed_name] = {
                    "feed_name": feed_name,
                    "feed_title": row.feed_title,
                    "group_name": row.group_name,
                    "http_request": row.http_request,
                    "access_date": row.access_date,
                    "view_date": row.view_date,
                    "feedmaker": row.feedmaker,
                    "update_date": row.rss_update_date,
                    "public_html": row.public_html,
                    "file_path": row.public_feed_file_path,
                    "upload_date": row.upload_date,
                }

        return feed_name_status_info_map

    @classmethod
    def _estimate_dir_size(cls, dir_path: Path) -> int:
        # du처럼 디스크 점유 크기(st_blocks)를 쓰되, 속도를 위해 파일 수는 stat 없이 세고
        # 균등 간격 표본의 평균 크기 × 파일 수로 전체 크기를 추정한다.
        # 파일 수가 표본 수 이하이면 모든 파일을 stat하므로 정확한 값이 된다.
        with os.scandir(dir_path) as it:
            files = [entry for entry in it if entry.is_file(follow_symlinks=False)]
        num_files = len(files)
        if num_files == 0:
            return 0
        step = max(1, num_files // cls.image_dir_size_sample_count)
        sample = files[::step]
        sample_size = sum(entry.stat(follow_symlinks=False).st_blocks * 512 for entry in sample)
        return sample_size * num_files // len(sample)

    @classmethod
    def get_feed_image_dir_size_map(cls) -> dict[str, FeedImageDirSizeInfo]:
        LOGGER.debug("# get_feed_image_dir_size_map()")
        img_dir_prefix = Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")
        if not img_dir_prefix or not Path(img_dir_prefix).is_dir():
            LOGGER.warning("can't find image directory '%s'", img_dir_prefix)
            return {}

        # 이미지는 그룹과 무관하게 WEB_SERVICE_IMAGE_DIR_PREFIX/<feed_name> 아래에 저장된다
        feed_name_size_map: dict[str, int] = {}
        with os.scandir(img_dir_prefix) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    feed_name_size_map[entry.name] = cls._estimate_dir_size(Path(entry.path))
        if not feed_name_size_map:
            return {}

        # 같은 feed_name의 행이 여럿이면 feedmaker=True인 행의 제목·그룹을 우선한다
        feed_name_title_group_map: dict[str, tuple[str, str]] = {}
        with DB.session_ctx() as s:
            rows = s.query(FeedInfo.feed_name, FeedInfo.feed_title, FeedInfo.group_name, FeedInfo.feedmaker).filter(FeedInfo.feed_name.in_(list(feed_name_size_map))).all()
            for row in rows:
                if row.feed_name not in feed_name_title_group_map or row.feedmaker:
                    feed_name_title_group_map[row.feed_name] = (row.feed_title or "", row.group_name or "")

        result: dict[str, FeedImageDirSizeInfo] = {}
        for feed_name, size in sorted(feed_name_size_map.items(), key=lambda item: item[1], reverse=True):
            feed_title, group_name = feed_name_title_group_map.get(feed_name, ("", ""))
            result[feed_name] = FeedImageDirSizeInfo(feed_name=feed_name, feed_title=feed_title, group_name=group_name, size=size)
        return result

    def update_feed_info(self, feed_dir_path: Path, new_feed_dir_path: Optional[Path] = None) -> None:
        LOGGER.debug("# update_feed_info(feed_dir_path=%s, new_feed_dir_path=%s)", PathUtil.short_path(feed_dir_path), PathUtil.short_path(new_feed_dir_path))
        if not new_feed_dir_path:
            new_feed_dir_path = feed_dir_path

        if not feed_dir_path.is_dir() and not new_feed_dir_path.is_dir():
            LOGGER.warning("can't find feed directory '%s' or '%s'", PathUtil.short_path(feed_dir_path), PathUtil.short_path(new_feed_dir_path))
        FeedManager.remove_config_info(feed_dir_path)
        FeedManager.remove_rss_info(feed_dir_path)
        self.feed_manager.remove_public_feed_by_feed_name(feed_dir_path.name)
        FeedManager.remove_progress_info(feed_dir_path)
        AccessLogManager.remove_httpd_access_info(feed_dir_path)
        self.html_file_manager.remove_html_file_in_path_from_info("feed_dir_path", feed_dir_path)

        FeedManager.add_config_info(new_feed_dir_path)
        FeedManager.add_rss_info(new_feed_dir_path)
        self.feed_manager.add_public_feed_by_feed_name(new_feed_dir_path.name)
        FeedManager.add_progress_info(new_feed_dir_path)
        self.html_file_manager.add_html_file(new_feed_dir_path)

    def load_all(self, max_num_feeds: Optional[int] = None, max_num_public_feeds: Optional[int] = None) -> int:
        LOGGER.debug("# load_all(max_num_feeds=%r, max_num_public_feeds=%r)", max_num_feeds, max_num_public_feeds)
        LOGGER.info("* start loading information")
        self.feed_manager.load_all(max_num_feeds=max_num_feeds, max_num_public_feeds=max_num_public_feeds)
        self.html_file_manager.load_all_html_files(max_num_feeds)
        return 0


if __name__ == "__main__":
    pm = ProblemManager()
    pm.load_all()
