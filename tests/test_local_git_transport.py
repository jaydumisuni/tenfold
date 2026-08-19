from pathlib import Path
import subprocess
import pytest
from tenfold.local_git_transport import LocalGitRepositoryTransport, LocalGitTransportError


def git(root, *args, input_text=None):
    p = subprocess.run(["git", "-C", str(root), *args], input=input_text, text=True, capture_output=True, check=True)
    return p.stdout.strip()


def make_repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    (root / "README.md").write_text("base\n", encoding="utf-8")
    git(root, "add", "README.md")
    git(root, "commit", "-m", "base")
    return root


def test_bounded_branch_and_commit_leave_main_unchanged(tmp_path):
    root = make_repo(tmp_path)
    transport = LocalGitRepositoryTransport({"tenfold": root})
    main = transport.resolve_ref("tenfold", "main")
    assert transport.read_file("tenfold", "README.md", main) == b"base\n"
    assert transport.create_branch("tenfold", "tf30/bounded", main) == main
    changed = transport.commit_files(
        "tenfold", "tf30/bounded", main,
        {"docs/tf30-proof.md": b"bounded\n", "README.md": b"base\nqualified\n"},
        "TF-30 bounded campaign\n",
    )
    assert changed != main
    assert transport.resolve_ref("tenfold", "main") == main
    assert transport.resolve_ref("tenfold", "tf30/bounded") == changed
    assert transport.read_file("tenfold", "docs/tf30-proof.md", changed) == b"bounded\n"
    assert transport.read_file("tenfold", "README.md", changed) == b"base\nqualified\n"


def test_expected_head_is_atomic_and_stale_writes_fail(tmp_path):
    root = make_repo(tmp_path)
    transport = LocalGitRepositoryTransport({"tenfold": root})
    main = transport.resolve_ref("tenfold", "main")
    transport.create_branch("tenfold", "tf30/bounded", main)
    new = transport.commit_files("tenfold", "tf30/bounded", main, {"one.txt": b"1"}, "one\n")
    with pytest.raises(LocalGitTransportError, match="expected-head"):
        transport.commit_files("tenfold", "tf30/bounded", main, {"two.txt": b"2"}, "two\n")
    assert transport.resolve_ref("tenfold", "tf30/bounded") == new


def test_transport_rejects_unregistered_escape_symlink_and_release_authority(tmp_path):
    root = make_repo(tmp_path)
    transport = LocalGitRepositoryTransport({"tenfold": root})
    main = transport.resolve_ref("tenfold", "main")
    with pytest.raises(LocalGitTransportError, match="not registered"):
        transport.resolve_ref("other", "main")
    with pytest.raises(LocalGitTransportError, match="escapes"):
        transport.read_file("tenfold", "../secret", main)
    with pytest.raises(LocalGitTransportError, match="pull-request authority"):
        transport.open_pull_request("tenfold", "main", "work", main, "x", "y")
    with pytest.raises(LocalGitTransportError, match="merge authority"):
        transport.merge_pull_request("tenfold", 1, main)

    link = tmp_path / "repo-link"
    link.symlink_to(root, target_is_directory=True)
    with pytest.raises(LocalGitTransportError, match="symlink"):
        LocalGitRepositoryTransport({"linked": link})


def test_bare_repository_is_supported_without_checkout(tmp_path):
    source = make_repo(tmp_path)
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "clone", "--bare", "--no-hardlinks", str(source), str(bare)], check=True, capture_output=True)
    transport = LocalGitRepositoryTransport({"tenfold": bare})
    main = transport.resolve_ref("tenfold", "main")
    transport.create_branch("tenfold", "tf30/bare", main)
    changed = transport.commit_files("tenfold", "tf30/bare", main, {"proof.txt": b"ok\n"}, "proof\n")
    assert transport.read_file("tenfold", "proof.txt", changed) == b"ok\n"
    assert transport.resolve_ref("tenfold", "main") == main


def test_pathspec_magic_is_rejected(tmp_path):
    root = make_repo(tmp_path)
    transport = LocalGitRepositoryTransport({"tenfold": root})
    main = transport.resolve_ref("tenfold", "main")
    with pytest.raises(LocalGitTransportError, match="invalid repository path"):
        transport.read_file("tenfold", "*.md", main)
