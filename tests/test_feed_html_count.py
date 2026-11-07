from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bin.feed_manager import FeedManager


@pytest.mark.parametrize("group,feed", [("group", "feed"), ("_group", "feed"), ("group", "_feed"), ("_group", "_feed")])
@pytest.mark.parametrize("has_html", [False, True])
def test_progress_responses_count_actual_html_files(tmp_path, group, feed, has_html):
    feed_dir = tmp_path / group / feed
    feed_dir.mkdir(parents=True)
    if has_html:
        html_dir = feed_dir / "html"
        html_dir.mkdir()
        (html_dir / "one.html").write_text("one")
        (html_dir / "two.html").write_text("two")
        (html_dir / "ignored.txt").write_text("ignored")
        (html_dir / "directory.html").mkdir()
    row = SimpleNamespace(
        feed_name="feed", group_name="group", feed_title="Feed", config="{}",
        config_modify_date=None, collect_date=None, total_item_count=20,
        public_feed_file_path="", file_size=0, num_items=0, upload_date=None,
        current_index=3, unit_size_per_day=1, progress_ratio=15, due_date=None,
    )
    session = MagicMock()
    session.query.return_value.where.return_value.all.return_value = [row]
    session.query.return_value.where.return_value.first.return_value = row
    with patch.object(FeedManager, "work_dir_path", tmp_path), patch("bin.feed_manager.DB.session_ctx") as context:
        context.return_value.__enter__.return_value = session
        progress = FeedManager.get_feed_name_progress_info_map()["feed"]
        detail = FeedManager.get_feed_info("group", "feed")
    assert progress["html_file_count"] == (2 if has_html else 0)
    assert detail["progress_info"]["html_file_count"] == (2 if has_html else 0)
    assert progress["total_item_count"] == 20
    assert detail["progress_info"]["total_item_count"] == 20
    assert detail["collection_info"]["total_item_count"] == 20
