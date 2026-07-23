#!/usr/bin/env python3
"""Read-only inventory for Progress Claw local data-retention review."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import stat
import time


@dataclass(frozen=True)
class RetentionCategory:
    name: str
    relative_path: str
    retention_days: int


@dataclass(frozen=True)
class RetentionSummary:
    name: str
    path: str
    retention_days: int
    files: int
    bytes: int
    expired_files: int
    expired_bytes: int
    oldest_age_days: float | None


CATEGORIES = (
    RetentionCategory(
        "player_history", "dashboard/assets/static/images/players", 7
    ),
    RetentionCategory(
        "raw_training_captures", "ai/training/yolo_people/raw_photos", 30
    ),
    RetentionCategory(
        "training_runs", "ai/training/yolo_people/runs", 30
    ),
    RetentionCategory("runtime_logs", "logs", 14),
)


def _regular_files(path: Path):
    if not path.is_dir():
        return
    for candidate in path.rglob("*"):
        try:
            file_status = candidate.lstat()
        except OSError:
            continue
        if stat.S_ISREG(file_status.st_mode) and candidate.name != ".gitkeep":
            yield candidate, file_status


def summarize_category(
    project_root: Path,
    category: RetentionCategory,
    *,
    now: float | None = None,
) -> RetentionSummary:
    current_time = time.time() if now is None else now
    cutoff = current_time - category.retention_days * 86400
    files = 0
    total_bytes = 0
    expired_files = 0
    expired_bytes = 0
    oldest_age_days = None
    category_path = project_root / category.relative_path

    for _path, file_status in _regular_files(category_path):
        files += 1
        total_bytes += file_status.st_size
        age_days = max(0.0, (current_time - file_status.st_mtime) / 86400)
        oldest_age_days = (
            age_days if oldest_age_days is None else max(oldest_age_days, age_days)
        )
        if file_status.st_mtime < cutoff:
            expired_files += 1
            expired_bytes += file_status.st_size

    return RetentionSummary(
        name=category.name,
        path=category.relative_path,
        retention_days=category.retention_days,
        files=files,
        bytes=total_bytes,
        expired_files=expired_files,
        expired_bytes=expired_bytes,
        oldest_age_days=(
            None if oldest_age_days is None else round(oldest_age_days, 2)
        ),
    )


def audit(project_root: Path, *, now: float | None = None) -> list[RetentionSummary]:
    return [
        summarize_category(project_root, category, now=now)
        for category in CATEGORIES
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory local retained data without deleting files"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Progress Claw project root",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()
    summaries = audit(args.root.resolve())

    if args.json:
        print(json.dumps({"categories": [asdict(item) for item in summaries]}, indent=2))
    else:
        print("Progress Claw data-retention audit (read-only)")
        for item in summaries:
            oldest = "none" if item.oldest_age_days is None else item.oldest_age_days
            print(
                f"{item.name}: files={item.files} bytes={item.bytes} "
                f"expired={item.expired_files} expired_bytes={item.expired_bytes} "
                f"oldest_days={oldest} limit_days={item.retention_days}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
