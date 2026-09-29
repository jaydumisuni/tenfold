from pathlib import Path


WORKFLOW = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")


def test_tenfold_ci_uses_owned_kratos_runner_and_blocks_fork_pr_execution():
    assert WORKFLOW.count("runs-on: [self-hosted, Linux, X64, kratos, tenfold]") == 2
    assert WORKFLOW.count("github.event.pull_request.head.repo.full_name == github.repository") == 2
    assert "runs-on: ubuntu-latest" not in WORKFLOW


def test_tenfold_ci_keeps_exact_candidate_and_full_qualification_gates():
    assert "Verify exact candidate head" in WORKFLOW
    assert "cargo test --workspace --locked" in WORKFLOW
    assert "python -m pytest -q" in WORKFLOW
    assert "TF-31 repository-only clean-clone qualification" in WORKFLOW
    assert "TENFOLD_REPOSITORY_ONLY_PROOF=1" in WORKFLOW
