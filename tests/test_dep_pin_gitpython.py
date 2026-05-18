#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `gitpython` (imported as `git`).

Purpose
-------
Pin the GitPython surface used by backend/feed_maker_manager.py's git
helpers (_git_add / _git_rm / _git_mv). A GitPython upgrade that changes
the index.add/remove/move signatures or moves `repo.git.ls_files()` will
break the feed-management endpoints' commit flow.

Reference call sites (production code):
    backend/feed_maker_manager.py:16   from git import Repo
    backend/feed_maker_manager.py:63   Repo(self.work_dir_path)
    backend/feed_maker_manager.py:70   repo.git.ls_files(rel_path).strip()
    backend/feed_maker_manager.py:72   repo.index.add([rel_path])
    backend/feed_maker_manager.py:73   repo.index.commit(f"{verb} {feed_name}")
    backend/feed_maker_manager.py:84   repo.index.remove([rel_path], r=True)
    backend/feed_maker_manager.py:96   repo.index.move([str(old), str(new)])
"""

import tempfile
import unittest
from pathlib import Path

from git import Repo


class _RepoFixture:
    """Creates an isolated git repo in a temp dir, with one initial commit."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self.repo = Repo.init(self.path)
        # GitPython needs a configured author for commits.
        with self.repo.config_writer() as cw:
            cw.set_value("user", "name", "Learning Test")
            cw.set_value("user", "email", "learning@test.local")
        # Seed file so the repo has HEAD.
        (self.path / "README").write_text("init\n")
        self.repo.index.add(["README"])
        self.repo.index.commit("init")

    def close(self) -> None:
        self._tmp.cleanup()


class GitPythonImportSurfaceTest(unittest.TestCase):
    def test_repo_is_a_class(self) -> None:
        self.assertTrue(isinstance(Repo, type))


class RepoConstructorTest(unittest.TestCase):
    """Pin Repo(path) -- production passes a Path object."""

    def test_repo_accepts_pathlib_path(self) -> None:
        f = _RepoFixture()
        try:
            r = Repo(f.path)  # Path, not str
            self.assertEqual(Path(r.working_tree_dir or "").resolve(), f.path.resolve())
        finally:
            f.close()


class RepoGitLsFilesTest(unittest.TestCase):
    """Pin repo.git.ls_files(rel_path).strip() used in _git_add."""

    def test_ls_files_returns_str_for_tracked_path(self) -> None:
        f = _RepoFixture()
        try:
            # README is tracked.
            out = f.repo.git.ls_files("README")
            self.assertIsInstance(out, str)
            self.assertEqual(out.strip(), "README")
        finally:
            f.close()

    def test_ls_files_returns_empty_str_for_untracked_path(self) -> None:
        # Production relies on: tracked = repo.git.ls_files(rel_path).strip()
        # to choose between "add" and "modify". Empty string == untracked.
        f = _RepoFixture()
        try:
            (f.path / "new_dir").mkdir()
            (f.path / "new_dir" / "x.txt").write_text("x")
            out = f.repo.git.ls_files("new_dir/x.txt").strip()
            self.assertEqual(out, "")
        finally:
            f.close()


class RepoIndexAddCommitTest(unittest.TestCase):
    """Pin repo.index.add([rel_path]) + repo.index.commit(msg)."""

    def test_index_add_accepts_list_of_rel_paths(self) -> None:
        f = _RepoFixture()
        try:
            (f.path / "feed").mkdir()
            (f.path / "feed" / "a.txt").write_text("a")
            f.repo.index.add(["feed/a.txt"])
            commit = f.repo.index.commit("add feed")
            # Returns a Commit object with a sha.
            self.assertTrue(hasattr(commit, "hexsha"))
            self.assertEqual(len(commit.hexsha), 40)
        finally:
            f.close()


class RepoIndexRemoveTest(unittest.TestCase):
    """Pin repo.index.remove([rel_path], r=True) used in _git_rm."""

    def test_remove_with_r_true_removes_directory(self) -> None:
        f = _RepoFixture()
        try:
            d = f.path / "feed"
            d.mkdir()
            (d / "a").write_text("a")
            (d / "b").write_text("b")
            f.repo.index.add(["feed/a", "feed/b"])
            f.repo.index.commit("seed")

            f.repo.index.remove(["feed"], r=True)
            f.repo.index.commit("remove feed")

            tracked = f.repo.git.ls_files("feed").strip()
            self.assertEqual(tracked, "")
        finally:
            f.close()


class RepoIndexMoveTest(unittest.TestCase):
    """Pin repo.index.move([old, new]) used in _git_mv."""

    def test_move_renames_path_in_index(self) -> None:
        f = _RepoFixture()
        try:
            (f.path / "old").mkdir()
            (f.path / "old" / "a").write_text("a")
            f.repo.index.add(["old/a"])
            f.repo.index.commit("seed")

            # Production uses absolute paths in the move call.
            old = f.path / "old"
            new = f.path / "new"
            f.repo.index.move([str(old), str(new)])
            f.repo.index.commit("rename")

            self.assertFalse((f.path / "old").exists())
            self.assertTrue((f.path / "new" / "a").is_file())
        finally:
            f.close()


if __name__ == "__main__":
    unittest.main()
