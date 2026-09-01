from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import os
import re
import shutil
import subprocess
import tempfile
from typing import Mapping


_SHA40 = re.compile(r"^[0-9a-fA-F]{40}$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class LocalGitTransportError(RuntimeError):
    pass


@dataclass(frozen=True)
class _RegisteredRepository:
    root: Path
    device: int
    inode: int


class LocalGitRepositoryTransport:
    """Model-free RepositoryTransport for explicitly registered local Git repositories.

    It intentionally provides only local ref/file/commit primitives. Pull-request and
    merge operations remain outside this transport's authority.
    """

    def __init__(
        self,
        repositories: Mapping[str, str | Path],
        *,
        git_executable: str | None = None,
        author_name: str = "Tenfold",
        author_email: str = "tenfold@local.invalid",
    ) -> None:
        resolved_git = git_executable or shutil.which("git")
        if not resolved_git:
            raise LocalGitTransportError("git executable is unavailable")
        self._git = str(Path(resolved_git).resolve())
        self._author_name = author_name
        self._author_email = author_email
        self._repositories: dict[str, _RegisteredRepository] = {}
        for name, value in repositories.items():
            if not _REPOSITORY.fullmatch(name):
                raise LocalGitTransportError(f"invalid repository identity: {name}")
            root = Path(value)
            if root.is_symlink():
                raise LocalGitTransportError(f"repository root cannot be a symlink: {name}")
            root = root.resolve(strict=True)
            if not root.is_dir():
                raise LocalGitTransportError(f"repository root is not a directory: {name}")
            stat = root.stat()
            registered = _RegisteredRepository(root, stat.st_dev, stat.st_ino)
            self._repositories[name] = registered
            self._run(name, "rev-parse", "--git-dir")

    def _repo(self, repository: str) -> _RegisteredRepository:
        registered = self._repositories.get(repository)
        if registered is None:
            raise LocalGitTransportError(f"repository is not registered: {repository}")
        root = registered.root
        if root.is_symlink() or not root.exists():
            raise LocalGitTransportError(f"repository identity changed: {repository}")
        stat = root.stat()
        if (stat.st_dev, stat.st_ino) != (registered.device, registered.inode):
            raise LocalGitTransportError(f"repository identity changed: {repository}")
        return registered

    def _environment(self, extra: Mapping[str, str] | None = None) -> dict[str, str]:
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_")
        }
        env.update(
            {
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
                "LC_ALL": "C",
                "LANG": "C",
            }
        )
        # Global/system config is deliberately blanked above, so this process never
        # inherits the operator's own `safe.directory` trust (some filesystems, e.g.
        # certain Windows drives, report no owner and trip git's dubious-ownership
        # check). Re-declare it here, scoped only to the roots this transport has
        # explicitly registered -- narrower than a blanket allow, and confined to
        # this subprocess's environment rather than any file on disk.
        safe_directories = sorted({str(registered.root) for registered in self._repositories.values()})
        for index, directory in enumerate(safe_directories):
            env[f"GIT_CONFIG_KEY_{index}"] = "safe.directory"
            env[f"GIT_CONFIG_VALUE_{index}"] = directory
        if safe_directories:
            env["GIT_CONFIG_COUNT"] = str(len(safe_directories))
        if extra:
            env.update(extra)
        return env

    def _run(
        self,
        repository: str,
        *args: str,
        input_bytes: bytes | None = None,
        extra_env: Mapping[str, str] | None = None,
    ) -> bytes:
        root = self._repo(repository).root
        process = subprocess.run(
            [self._git, "-C", str(root), *args],
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            env=self._environment(extra_env),
            check=False,
        )
        if process.returncode != 0:
            detail = process.stderr.decode("utf-8", "replace").strip()
            raise LocalGitTransportError(
                f"git operation failed ({args[0] if args else 'unknown'}): {detail or process.returncode}"
            )
        return process.stdout

    @staticmethod
    def _full_sha(value: str) -> str:
        if not _SHA40.fullmatch(value):
            raise LocalGitTransportError("expected a full 40-character commit SHA")
        return value.lower()

    @staticmethod
    def _ref(value: str) -> str:
        if _SHA40.fullmatch(value):
            return value.lower()
        if not _REF.fullmatch(value):
            raise LocalGitTransportError(f"invalid Git ref: {value}")
        if (
            value.startswith("-")
            or value.endswith(".")
            or value.endswith(".lock")
            or ".." in value
            or "//" in value
            or "@{" in value
            or "\\" in value
        ):
            raise LocalGitTransportError(f"invalid Git ref: {value}")
        return value

    def _branch(self, repository: str, branch: str) -> str:
        branch = self._ref(branch)
        if _SHA40.fullmatch(branch) or branch == "HEAD":
            raise LocalGitTransportError("branch name cannot be a commit identity")
        self._run(repository, "check-ref-format", "--branch", branch)
        return branch

    @staticmethod
    def _path(value: str) -> str:
        if not value or any(ch in value for ch in ("\x00", "\r", "\n", "\\", ":", "*", "?", "[", "]")):
            raise LocalGitTransportError(f"invalid repository path: {value}")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise LocalGitTransportError(f"repository path escapes root: {value}")
        normalized = "/".join(part for part in path.parts if part not in {"", "."})
        if not normalized or normalized.startswith("-"):
            raise LocalGitTransportError(f"invalid repository path: {value}")
        return normalized

    def resolve_ref(self, repository: str, ref: str) -> str:
        safe_ref = self._ref(ref)
        output = self._run(
            repository,
            "rev-parse",
            "--verify",
            "--end-of-options",
            f"{safe_ref}^{{commit}}",
        ).decode("ascii", "strict").strip()
        return self._full_sha(output)

    def read_file(self, repository: str, path: str, ref: str) -> bytes:
        safe_path = self._path(path)
        exact_ref = self.resolve_ref(repository, ref)
        return self._run(repository, "cat-file", "blob", f"{exact_ref}:{safe_path}")

    def create_branch(self, repository: str, branch: str, from_sha: str) -> str:
        safe_branch = self._branch(repository, branch)
        exact_base = self._full_sha(from_sha)
        if self.resolve_ref(repository, exact_base) != exact_base:
            raise LocalGitTransportError("branch base does not resolve to the expected commit")
        zero = "0" * 40
        self._run(repository, "update-ref", f"refs/heads/{safe_branch}", exact_base, zero)
        return self.resolve_ref(repository, safe_branch)

    def _mode_for_path(self, repository: str, commit: str, path: str) -> str:
        output = self._run(repository, "ls-tree", commit, "--", path).decode("utf-8", "strict").strip()
        if not output:
            return "100644"
        mode = output.split(None, 1)[0]
        if mode not in {"100644", "100755"}:
            raise LocalGitTransportError(f"refusing to replace non-regular Git entry: {path}")
        return mode

    def commit_files(
        self,
        repository: str,
        branch: str,
        expected_head: str,
        files: dict[str, bytes],
        message: str,
    ) -> str:
        safe_branch = self._branch(repository, branch)
        exact_head = self._full_sha(expected_head)
        if self.resolve_ref(repository, safe_branch) != exact_head:
            raise LocalGitTransportError("repository expected-head fence failed")
        if not files:
            raise LocalGitTransportError("commit requires at least one file")
        if not message or "\x00" in message or len(message) > 8192:
            raise LocalGitTransportError("invalid commit message")

        normalized_files: dict[str, bytes] = {}
        for path, content in files.items():
            safe_path = self._path(path)
            if safe_path in normalized_files:
                raise LocalGitTransportError(f"duplicate normalized path: {safe_path}")
            if not isinstance(content, bytes):
                raise LocalGitTransportError(f"repository content must be bytes: {safe_path}")
            normalized_files[safe_path] = content

        with tempfile.TemporaryDirectory(prefix="tenfold-git-index-") as temporary:
            index_path = str(Path(temporary) / "index")
            index_env = {"GIT_INDEX_FILE": index_path}
            self._run(repository, "read-tree", exact_head, extra_env=index_env)
            for path, content in sorted(normalized_files.items()):
                blob = self._run(repository, "hash-object", "-w", "--stdin", input_bytes=content).decode(
                    "ascii", "strict"
                ).strip()
                if not _SHA40.fullmatch(blob):
                    raise LocalGitTransportError("git returned an invalid blob identity")
                mode = self._mode_for_path(repository, exact_head, path)
                self._run(
                    repository,
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    mode,
                    blob,
                    path,
                    extra_env=index_env,
                )
            tree = self._run(repository, "write-tree", extra_env=index_env).decode("ascii", "strict").strip()
            if not _SHA40.fullmatch(tree):
                raise LocalGitTransportError("git returned an invalid tree identity")

        identity_env = {
            "GIT_AUTHOR_NAME": self._author_name,
            "GIT_AUTHOR_EMAIL": self._author_email,
            "GIT_COMMITTER_NAME": self._author_name,
            "GIT_COMMITTER_EMAIL": self._author_email,
        }
        new_commit = self._run(
            repository,
            "commit-tree",
            tree,
            "-p",
            exact_head,
            input_bytes=message.encode("utf-8"),
            extra_env=identity_env,
        ).decode("ascii", "strict").strip()
        new_commit = self._full_sha(new_commit)
        self._run(
            repository,
            "update-ref",
            f"refs/heads/{safe_branch}",
            new_commit,
            exact_head,
        )
        return new_commit

    def open_pull_request(
        self,
        repository: str,
        base: str,
        head: str,
        expected_head: str,
        title: str,
        body: str,
    ) -> tuple[str, int]:
        raise LocalGitTransportError("local Git transport has no pull-request authority")

    def merge_pull_request(self, repository: str, pr_number: int, expected_head: str) -> str:
        raise LocalGitTransportError("local Git transport has no merge authority")
