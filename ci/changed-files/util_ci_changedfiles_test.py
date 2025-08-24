#!/usr/bin/env python3
import pytest
from pathlib import Path
import git
import util_ci_changedfiles as cf


@pytest.fixture
def repo_fixture(tmp_path: Path, monkeypatch):
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "tony stark").release()
    repo.config_writer().set_value("user", "email", "stark@avengers.com").release()
    repo.create_remote("origin", url="https://marvel.com/heroes.git")
    repo.git.commit("--allow-empty", "-m", "initial commit")
    if "main" not in repo.heads:
        repo.create_head("main")
    repo.head.reference = repo.heads.main
    repo.head.reset(index=True, working_tree=True)
    monkeypatch.chdir(tmp_path)
    return repo


def commit_file(repo: git.Repo, name: str, content: str):
    f = Path(repo.working_tree_dir) / name
    f.write_text(content)
    repo.index.add([str(f)])
    repo.index.commit(f"add {name}")
    return f


def test_changed_files(repo_fixture: git.Repo):
    f = commit_file(repo_fixture, "ironman.txt", "i am iron man")
    f.write_text("snap")
    files = cf.diff_finder()
    assert files == ["ironman.txt"]


def test_untracked_files(repo_fixture: git.Repo):
    f = Path(repo_fixture.working_tree_dir) / "spiderman.py"
    f.write_text("with great power...")
    files = cf.diff_finder(untracked=True)
    assert files == ["spiderman.py"]


def test_include_exclude(repo_fixture: git.Repo):
    thor = commit_file(repo_fixture, "thor.py", "mjolnir")
    hulk = commit_file(repo_fixture, "hulk.txt", "smash")
    thor.write_text("lightning")
    hulk.write_text("angry")
    files = cf.diff_finder(include=["*.py"], exclude=["hulk.*"])
    assert files == ["thor.py"]


def test_ci_mode(monkeypatch, repo_fixture: git.Repo):
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    monkeypatch.setenv("GITHUB_HEAD_REF", "fix_add_all_the_party")
    commit_file(repo_fixture, "ironman.txt", "avengers assemble")
    repo_fixture.create_head("origin/main", repo_fixture.head.commit)
    repo_fixture.git.checkout("-b", "fix_add_all_the_party")
    wid = Path(repo_fixture.working_tree_dir) / "blackwidow.py"
    wid.write_text("spy")
    repo_fixture.index.add([str(wid)])
    repo_fixture.index.commit("add black widow")
    repo_fixture.create_head("origin/fix_add_all_the_party", repo_fixture.head.commit)
    files = cf.diff_finder()
    assert sorted(files) == ["blackwidow.py"]


def test_ci_untracked(monkeypatch, repo_fixture: git.Repo):
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")
    monkeypatch.setenv("GITHUB_HEAD_REF", "fix_add_all_the_party")
    f = Path(repo_fixture.working_tree_dir) / "hawkeye.py"
    f.write_text("arrows")
    files = cf.diff_finder(untracked=True)
    assert files == ["hawkeye.py"]
