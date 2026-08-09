import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from rich.console import Console

from src.models import ContentItem, FilteringConfig, SourceType
from src.orchestrator import HorizonOrchestrator
from src.storage.manager import StorageManager


def make_item(item_id: str, score: float, status: str | None = None) -> ContentItem:
    metadata: dict[str, object] = {}
    if status is not None:
        metadata["teacher_editorial_status"] = status
    return ContentItem(
        id=item_id,
        source_type=SourceType.RSS,
        title=item_id,
        url=f"https://example.com/{item_id}",
        published_at=datetime.now(timezone.utc),
        ai_score=score,
        metadata=metadata,
    )


def make_orchestrator() -> HorizonOrchestrator:
    orchestrator = HorizonOrchestrator.__new__(HorizonOrchestrator)
    orchestrator.config = SimpleNamespace(
        filtering=FilteringConfig(ai_score_threshold=7.0, repeat_cooldown_days=7)
    )
    orchestrator.console = Console(record=True)
    orchestrator.storage = SimpleNamespace()
    return orchestrator


def test_editorial_decision_can_admit_useful_low_scored_item() -> None:
    orchestrator = make_orchestrator()
    result = asyncio.run(
        orchestrator.filter_items(
            [
                make_item("include-low-score", 5.0, "include"),
                make_item("watch-high-score", 9.0, "watch"),
                make_item("legacy-score", 8.0),
            ],
            topic_dedup=False,
            editorial_status_key="teacher_editorial_status",
        )
    )

    assert [item.id for item in result.items] == [
        "legacy-score",
        "include-low-score",
    ]


def test_recent_selected_source_is_kept_out_of_formal_selection() -> None:
    fresh, repeated = HorizonOrchestrator._exclude_recent_selected_items(
        [make_item("old", 9.0), make_item("new", 6.0)], {"old"}
    )

    assert [item.id for item in fresh] == ["new"]
    assert [item.id for item in repeated] == ["old"]


def test_selection_history_honours_cooldown_and_records_only_selected(tmp_path) -> None:
    storage = StorageManager(str(tmp_path))
    storage.record_selected_ids("2026-08-09", {"item-a", "item-b"})

    assert storage.load_recent_selected_ids("2026-08-12", 7) == {"item-a", "item-b"}
    assert storage.load_recent_selected_ids("2026-08-20", 7) == set()


def test_quality_review_reports_gates_not_weighted_score() -> None:
    orchestrator = make_orchestrator()
    review = orchestrator._daily_quality_review(
        [make_item("parent", 2.0)], [make_item("teacher", 10.0)]
    )

    assert "/10" not in str(review["markdown"])
    assert "正式选题硬门槛：通过" in str(review["markdown"])
