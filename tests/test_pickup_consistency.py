from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pickup_tracks_canonical_g2_28_progress_without_claiming_completion():
    pickup = (ROOT / "PICKUP.md").read_text(encoding="utf-8")
    review = (ROOT / "docs" / "gen2" / "G2-28-review-record.md").read_text(encoding="utf-8")

    assert "Current Gen-2 milestone: **G2-28 IN PROGRESS**" in pickup
    assert "G2-28 remains **NOT COMPLETE**" in pickup
    assert "Current next Gen-2 milestone: **none advanced**" not in pickup

    assert "This slice does **not** claim that Acceptance is satisfied." in review
    assert "STABILIZATION_PROVEN" in review
    assert "IRREVERSIBLY_COMMITTED" in review
