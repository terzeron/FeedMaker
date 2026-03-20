#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from git import Repo

from backend.feed_maker_manager import FeedMakerManager, _validate_name


@pytest.fixture
def git_repo(tmp_path):
    """임시 git 저장소 생성"""
    repo = Repo.init(tmp_path)
    # 초기 커밋 생성
    readme = tmp_path / "README.md"
    readme.write_text("init")
    repo.index.add(["README.md"])
    repo.index.commit("initial commit")
    return repo, tmp_path


@pytest.fixture
def manager(git_repo):
    """FeedMakerManager를 임시 git 저장소로 패치"""
    repo, tmp_path = git_repo
    with (
        patch.object(FeedMakerManager, "__init__", lambda self: None),
        patch.object(FeedMakerManager, "work_dir_path", tmp_path),
    ):
        mgr = FeedMakerManager.__new__(FeedMakerManager)
        mgr.work_dir_path = tmp_path
        yield mgr


class TestGitAdd:
    def test_adds_and_commits_file(self, manager, git_repo):
        repo, tmp_path = git_repo
        feed_dir = tmp_path / "test_group" / "test_feed"
        feed_dir.mkdir(parents=True)
        conf_file = feed_dir / "conf.json"
        conf_file.write_text('{"key": "value"}')

        result, error = manager._git_add(feed_dir)

        assert error is None
        assert "test_feed" in result
        # 커밋이 생성되었는지 확인
        last_commit = repo.head.commit
        assert "add test_feed" in last_commit.message

    def test_special_chars_in_feed_name_no_injection(self, manager, git_repo):
        """명령어 주입 시도가 안전하게 처리되는지 확인"""
        repo, tmp_path = git_repo
        malicious_name = "feed'; rm -rf /"
        feed_dir = tmp_path / "group" / malicious_name
        feed_dir.mkdir(parents=True)
        conf_file = feed_dir / "conf.json"
        conf_file.write_text("{}")

        result, error = manager._git_add(feed_dir)

        # 셸 실행 없이 안전하게 커밋됨
        assert error is None
        assert "add" in result
        # 파일 시스템이 정상 상태인지 확인 (rm -rf 실행 안 됨)
        assert (tmp_path / "README.md").exists()


class TestGitRm:
    def test_removes_and_commits(self, manager, git_repo):
        repo, tmp_path = git_repo
        feed_dir = tmp_path / "group" / "feed_to_remove"
        feed_dir.mkdir(parents=True)
        conf_file = feed_dir / "conf.json"
        conf_file.write_text("{}")
        repo.index.add([str(conf_file.relative_to(tmp_path))])
        repo.index.commit("add feed_to_remove")

        result, error = manager._git_rm(feed_dir)

        assert error is None
        assert "feed_to_remove" in result
        last_commit = repo.head.commit
        assert "remove feed_to_remove" in last_commit.message

    def test_rm_nonexistent_returns_error(self, manager, git_repo):
        """존재하지 않는 파일 삭제 시 에러 반환"""
        _, tmp_path = git_repo
        feed_dir = tmp_path / "group" / "nonexistent"

        result, error = manager._git_rm(feed_dir)

        assert error is not None
        assert result == ""


class TestGitMv:
    def test_moves_and_commits(self, manager, git_repo):
        repo, tmp_path = git_repo
        src_dir = tmp_path / "group" / "old_feed"
        src_dir.mkdir(parents=True)
        conf_file = src_dir / "conf.json"
        conf_file.write_text("{}")
        repo.index.add([str(conf_file.relative_to(tmp_path))])
        repo.index.commit("add old_feed")

        dst_dir = tmp_path / "group" / "new_feed"

        result, error = manager._git_mv(src_dir, dst_dir)

        assert error is None
        assert "new_feed" in result

    def test_mv_fallback_to_shutil(self, manager, git_repo):
        """git mv 실패 시 shutil.move 폴백"""
        _, tmp_path = git_repo
        src_dir = tmp_path / "untracked_dir"
        src_dir.mkdir(parents=True)
        (src_dir / "file.txt").write_text("data")

        dst_dir = tmp_path / "moved_dir"

        result, error = manager._git_mv(src_dir, dst_dir)

        # git mv 실패 → shutil.move로 폴백 성공
        assert error is None
        assert dst_dir.exists()
        assert not src_dir.exists()

    def test_mv_special_chars_no_injection(self, manager, git_repo):
        """명령어 주입 시도가 안전하게 처리되는지 확인"""
        repo, tmp_path = git_repo
        src_dir = tmp_path / "group" / "normal_feed"
        src_dir.mkdir(parents=True)
        conf_file = src_dir / "conf.json"
        conf_file.write_text("{}")
        repo.index.add([str(conf_file.relative_to(tmp_path))])
        repo.index.commit("add normal_feed")

        malicious_name = "feed && rm -rf /"
        dst_dir = tmp_path / "group" / malicious_name

        result, error = manager._git_mv(src_dir, dst_dir)

        # 에러가 나든 폴백이든, 셸 명령어 주입은 발생하지 않음
        assert error is None


class TestValidateName:
    """경로 탐색 공격 방지를 위한 이름 검증 테스트"""

    def test_valid_names(self):
        # 정상 이름은 통과
        _validate_name("my_feed", "feed_name")
        _validate_name("group-name", "group_name")
        _validate_name("feed.v2", "feed_name")
        _validate_name("한글그룹", "group_name")
        _validate_name("_inactive_feed", "feed_name")
        _validate_name("Feed123", "feed_name")

    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError):
            _validate_name("../../etc", "group_name")

    def test_slash_rejected(self):
        with pytest.raises(ValueError):
            _validate_name("group/subdir", "group_name")

    def test_backslash_rejected(self):
        with pytest.raises(ValueError):
            _validate_name("group\\subdir", "group_name")

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            _validate_name("", "feed_name")

    def test_semicolon_rejected(self):
        with pytest.raises(ValueError):
            _validate_name("feed;rm -rf /", "feed_name")

    def test_space_rejected(self):
        with pytest.raises(ValueError):
            _validate_name("feed name", "feed_name")

    def test_shell_special_chars_rejected(self):
        for char in ["'", '"', "`", "$", "|", "&", "(", ")", "<", ">"]:
            with pytest.raises(ValueError):
                _validate_name(f"feed{char}test", "feed_name")


class TestDefusedXmlSecurity:
    """defusedxml이 악성 XML(XXE, XML bomb)을 거부하는지 확인"""

    def test_xxe_attack_rejected(self, manager, tmp_path):
        """XXE(XML External Entity) 공격이 거부되는지 확인"""
        xxe_xml = """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<rss><channel>
  <item><title>&xxe;</title></item>
</channel></rss>"""
        feed_dir = tmp_path / "feeds"
        feed_dir.mkdir(exist_ok=True)
        malicious_file = feed_dir / "evil.xml"
        malicious_file.write_text(xxe_xml)

        with (
            patch.object(type(manager), "feed_manager", create=True),
            patch("bin.feed_manager.FeedManager.public_feed_dir_path", feed_dir),
        ):
            result, error = manager.extract_titles_from_public_feed("evil")

        # defusedxml은 DTD/엔티티를 거부하므로 파싱 에러 발생
        assert result == "PARSE_ERROR"

    def test_xml_bomb_rejected(self, manager, tmp_path):
        """XML bomb(Billion Laughs) 공격이 거부되는지 확인"""
        bomb_xml = """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<rss><channel>
  <item><title>&lol3;</title></item>
</channel></rss>"""
        feed_dir = tmp_path / "feeds"
        feed_dir.mkdir(exist_ok=True)
        bomb_file = feed_dir / "bomb.xml"
        bomb_file.write_text(bomb_xml)

        with (
            patch.object(type(manager), "feed_manager", create=True),
            patch("bin.feed_manager.FeedManager.public_feed_dir_path", feed_dir),
        ):
            result, error = manager.extract_titles_from_public_feed("bomb")

        assert result == "PARSE_ERROR"

    def test_normal_xml_parsed_successfully(self, manager, tmp_path):
        """정상 XML은 올바르게 파싱되는지 확인"""
        normal_xml = """<?xml version="1.0"?>
<rss><channel>
  <item><title>정상 제목</title></item>
  <item><title>Normal Title</title></item>
</channel></rss>"""
        feed_dir = tmp_path / "feeds"
        feed_dir.mkdir(exist_ok=True)
        normal_file = feed_dir / "normal.xml"
        normal_file.write_text(normal_xml)

        with (
            patch.object(type(manager), "feed_manager", create=True),
            patch("bin.feed_manager.FeedManager.public_feed_dir_path", feed_dir),
        ):
            result, error = manager.extract_titles_from_public_feed("normal")

        assert isinstance(result, list)
        assert result == ["정상 제목", "Normal Title"]
        assert error == ""


class TestPathTraversalBlocked:
    """경로 탐색이 실제 메서드에서 차단되는지 확인"""

    def test_get_site_config_blocks_traversal(self, manager):
        with pytest.raises(ValueError):
            manager.get_site_config("../../etc")

    def test_save_site_config_blocks_traversal(self, manager):
        with pytest.raises(ValueError):
            manager.save_site_config("../../etc", {"key": "value"})

    def test_remove_html_file_blocks_traversal(self, manager):
        with pytest.raises(ValueError):
            manager.remove_html_file("group", "feed", "../../etc/passwd")

    def test_remove_feed_blocks_traversal(self, manager):
        with pytest.raises(ValueError):
            manager.remove_feed("../../", "etc")

    def test_remove_group_blocks_traversal(self, manager):
        with pytest.raises(ValueError):
            manager.remove_group("../../etc")
