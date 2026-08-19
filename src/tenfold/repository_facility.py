from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import sqlite3
from typing import Protocol

from .contracts import TaskPacket
from .facility import FacilityError, FacilityEvidence, FacilityKind, stable_digest, validate_live_task


class RepositoryTransport(Protocol):
    def resolve_ref(self, repository: str, ref: str) -> str: ...
    def read_file(self, repository: str, path: str, ref: str) -> bytes: ...
    def create_branch(self, repository: str, branch: str, from_sha: str) -> str: ...
    def commit_files(self, repository: str, branch: str, expected_head: str, files: dict[str, bytes], message: str) -> str: ...
    def open_pull_request(self, repository: str, base: str, head: str, expected_head: str, title: str, body: str) -> tuple[str, int]: ...
    def merge_pull_request(self, repository: str, pr_number: int, expected_head: str) -> str: ...


@dataclass(frozen=True)
class RepositoryReceipt:
    operation_id: str
    request_digest: str
    result_digest: str
    result: str


def repository_ref_resource(repository: str, ref: str) -> str:
    return f"repository:{repository}:ref:{ref}"


def repository_pr_resource(repository: str, pr_number: int) -> str:
    return f"repository:{repository}:pr:{pr_number}"


def repository_request_binding(operation: str, **fields) -> str:
    return stable_digest({"facility": "repository", "operation": operation, **fields})


def _path_parts(value: str) -> tuple[str, ...]:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise FacilityError(f"repository path escapes task scope: {value}")
    return tuple(part for part in path.parts if part not in {".", "/"})


def _path_in_scope(path: str, scopes: tuple[str, ...]) -> bool:
    target = _path_parts(path)
    for scope in scopes:
        allowed = _path_parts(scope)
        if not allowed or target[: len(allowed)] == allowed:
            return True
    return False


def _file_digests(files: dict[str, bytes]) -> dict[str, str]:
    return {path: stable_digest(data.hex()) for path, data in sorted(files.items())}


class RepositoryStateStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS receipts(
                    operation_id TEXT PRIMARY KEY,
                    request_digest TEXT NOT NULL,
                    result_digest TEXT NOT NULL,
                    result TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS writers(
                    repository TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    PRIMARY KEY(repository, branch)
                );
                """
            )

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def receipt(self, operation_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT operation_id,request_digest,result_digest,result FROM receipts WHERE operation_id=?",
                (operation_id,),
            ).fetchone()
        return None if row is None else RepositoryReceipt(*row)

    def put_receipt(self, receipt):
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO receipts VALUES(?,?,?,?)",
                    (receipt.operation_id, receipt.request_digest, receipt.result_digest, receipt.result),
                )
        except sqlite3.IntegrityError:
            prior = self.receipt(receipt.operation_id)
            if prior != receipt:
                raise FacilityError("repository operation raced with conflicting receipt")

    def acquire_writer(self, repository, branch, owner):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT owner FROM writers WHERE repository=? AND branch=?", (repository, branch)
            ).fetchone()
            if row:
                if row[0] != owner:
                    raise FacilityError("repository branch already has a mutable owner")
                return
            connection.execute("INSERT INTO writers VALUES(?,?,?)", (repository, branch, owner))

    def claim_writer(self, repository, branch, owner):
        """Mirror the already-validated durable lease owner into facility-local state."""
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO writers(repository,branch,owner) VALUES(?,?,?) "
                "ON CONFLICT(repository,branch) DO UPDATE SET owner=excluded.owner",
                (repository, branch, owner),
            )

    def writer(self, repository, branch):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT owner FROM writers WHERE repository=? AND branch=?", (repository, branch)
            ).fetchone()
        return None if row is None else row[0]

    def release_writer(self, repository, branch, owner):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT owner FROM writers WHERE repository=? AND branch=?", (repository, branch)
            ).fetchone()
            if not row or row[0] != owner:
                raise FacilityError("repository writer release does not match owner")
            connection.execute("DELETE FROM writers WHERE repository=? AND branch=?", (repository, branch))


class RepositoryFacility:
    read_capability = "repository.read"
    write_capability = "repository.write"

    def __init__(self, transport, state_store, authority_store):
        self.transport = transport
        self.state = state_store
        self.authority_store = authority_store

    def _idempotent(self, operation_id, request, perform):
        digest = stable_digest(request)
        prior = self.state.receipt(operation_id)
        if prior:
            if prior.request_digest != digest:
                raise FacilityError("repository operation id reused with different request")
            return prior
        result = str(perform())
        receipt = RepositoryReceipt(operation_id, digest, stable_digest(result), result)
        self.state.put_receipt(receipt)
        return receipt

    def acquire_writer(self, repository, branch, owner):
        self.state.acquire_writer(repository, branch, owner)

    def release_writer(self, repository, branch, owner):
        self.state.release_writer(repository, branch, owner)

    def _live_mutable(
        self,
        task: TaskPacket,
        *,
        resource: str,
        foreman_epoch: int,
        request_binding: str,
        owner: str | None = None,
    ):
        if owner is not None and owner != task.assignment_id:
            raise FacilityError("repository writer owner must equal assignment identity")
        return validate_live_task(
            task,
            self.authority_store,
            capability=self.write_capability,
            permission="write",
            foreman_epoch=foreman_epoch,
            require_lease=True,
            lease_resource=resource,
            request_binding=request_binding,
        )

    def create_branch(self, task, *, repository, branch, owner, base_ref, expected_base_sha, operation_id, foreman_epoch):
        request = {
            "operation_id": operation_id,
            "repository": repository,
            "branch": branch,
            "owner": owner,
            "base_ref": base_ref,
            "expected_base_sha": expected_base_sha,
        }
        self._live_mutable(
            task,
            resource=repository_ref_resource(repository, branch),
            foreman_epoch=foreman_epoch,
            owner=owner,
            request_binding=repository_request_binding("create_branch", **request),
        )
        if self.transport.resolve_ref(repository, base_ref) != expected_base_sha:
            raise FacilityError("repository branch base moved")
        self.state.claim_writer(repository, branch, task.assignment_id)
        return self._idempotent(
            operation_id,
            {"op": "create_branch", **request},
            lambda: self.transport.create_branch(repository, branch, expected_base_sha),
        )

    def read(self, task, *, repository, path, ref, expected_sha, request_id, foreman_epoch):
        if not _path_in_scope(path, task.scope):
            raise FacilityError(f"repository read outside task scope: {path}")
        request = {
            "request_id": request_id,
            "repository": repository,
            "path": path,
            "ref": ref,
            "expected_sha": expected_sha,
        }
        validate_live_task(
            task,
            self.authority_store,
            capability=self.read_capability,
            permission="read",
            foreman_epoch=foreman_epoch,
            request_binding=repository_request_binding("read", **request),
        )
        actual = self.transport.resolve_ref(repository, ref)
        if actual != expected_sha:
            raise FacilityError(f"repository ref moved: expected {expected_sha}, got {actual}")
        content = self.transport.read_file(repository, path, actual)
        return content, FacilityEvidence(
            FacilityKind.REPOSITORY,
            request_id,
            task.task_id,
            task.assignment_id,
            task.attempt,
            task.source_binding,
            stable_digest({"op": "read", **request}),
            True,
            "completed",
            (f"resolved_sha={actual}", f"content_sha256={stable_digest(content.hex())}"),
        )

    def commit(self, task, *, repository, branch, owner, expected_head, files, message, operation_id, foreman_epoch):
        escaped = tuple(path for path in files if not _path_in_scope(path, task.scope))
        if escaped:
            raise FacilityError(f"repository write outside task scope: {escaped}")
        request = {
            "operation_id": operation_id,
            "repository": repository,
            "branch": branch,
            "owner": owner,
            "expected_head": expected_head,
            "files": _file_digests(files),
            "message": message,
        }
        self._live_mutable(
            task,
            resource=repository_ref_resource(repository, branch),
            foreman_epoch=foreman_epoch,
            owner=owner,
            request_binding=repository_request_binding("commit", **request),
        )
        self.state.claim_writer(repository, branch, task.assignment_id)
        if self.transport.resolve_ref(repository, branch) != expected_head:
            raise FacilityError("repository expected-head fence failed")
        return self._idempotent(
            operation_id,
            {"op": "commit", **request},
            lambda: self.transport.commit_files(repository, branch, expected_head, files, message),
        )

    def open_pr(self, task, *, repository, base, head, expected_head, title, body, operation_id, foreman_epoch):
        request = {
            "operation_id": operation_id,
            "repository": repository,
            "base": base,
            "head": head,
            "expected_head": expected_head,
            "title": title,
            "body": body,
        }
        self._live_mutable(
            task,
            resource=repository_ref_resource(repository, head),
            foreman_epoch=foreman_epoch,
            request_binding=repository_request_binding("open_pr", **request),
        )
        if self.transport.resolve_ref(repository, head) != expected_head:
            raise FacilityError("PR expected-head fence failed")
        return self._idempotent(
            operation_id,
            {"op": "open_pr", **request},
            lambda: self.transport.open_pull_request(repository, base, head, expected_head, title, body),
        )

    def merge_pr(self, task, *, repository, pr_number, expected_head, operation_id, foreman_epoch):
        request = {
            "operation_id": operation_id,
            "repository": repository,
            "pr_number": pr_number,
            "expected_head": expected_head,
        }
        self._live_mutable(
            task,
            resource=repository_pr_resource(repository, pr_number),
            foreman_epoch=foreman_epoch,
            request_binding=repository_request_binding("merge_pr", **request),
        )
        return self._idempotent(
            operation_id,
            {"op": "merge_pr", **request},
            lambda: self.transport.merge_pull_request(repository, pr_number, expected_head),
        )
