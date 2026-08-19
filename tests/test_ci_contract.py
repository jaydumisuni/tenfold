from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_ci_runs_on_pull_requests_and_main_pushes():
    text = workflow_text()
    assert "pull_request:" in text
    assert "push:" in text
    assert "branches: [main]" in text


def test_ci_token_is_read_only_and_checkout_credentials_are_not_persisted():
    text = workflow_text()
    assert "permissions:\n  contents: read" in text
    assert "persist-credentials: false" in text


def test_ci_actions_are_pinned_to_immutable_commits():
    text = workflow_text()
    assert "actions/checkout@11d5960a326750d5838078e36cf38b85af677262" in text
    assert "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065" in text
    assert "actions/checkout@v4" not in text
    assert "actions/setup-python@v5" not in text


def test_ci_binds_checkout_and_proof_to_exact_candidate_sha():
    text = workflow_text()
    expression = "${{ github.event.pull_request.head.sha || github.sha }}"
    assert f"ref: {expression}" in text
    assert "fetch-depth: 1" in text
    assert "git rev-parse HEAD" in text
    assert expression in text


def test_ci_installs_declared_full_test_environment_and_runs_compile_and_suite():
    text = workflow_text()
    assert "python -m pip install -e '.[dev,browser]'" in text
    assert "python -m compileall -q src" in text
    assert "python -m pytest -q" in text


def test_tf31_ci_rebuilds_from_repository_only_fresh_git_state():
    text = workflow_text()
    assert "TF-31 repository-only clean-clone qualification" in text
    assert 'git init "$CLEAN"' in text
    assert 'git -C "$CLEAN" fetch --no-tags --depth=1 "$GITHUB_WORKSPACE" "$TENFOLD_CANDIDATE_SHA"' in text
    assert 'git -C "$CLEAN" checkout --detach FETCH_HEAD' in text
    assert 'test "$(git -C "$CLEAN" rev-parse HEAD)" = "$TENFOLD_CANDIDATE_SHA"' in text
    assert 'test -z "$(git -C "$CLEAN" status --porcelain)"' in text
    assert '"$VENV/bin/python" -m pip install "$CLEAN[dev,browser]"' in text
    assert "TENFOLD_REPOSITORY_ONLY_PROOF=1" in text
