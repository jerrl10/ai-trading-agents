from __future__ import annotations

import os
from pathlib import Path


def get_reports_base() -> Path:
    """
    Resolve the root directory for generated reports.

    Uses REPORTS_DIR env var when set, otherwise defaults to
    <project_root>/data/reports to keep assets inside the repo.
    """
    default_path = Path(__file__).resolve().parents[2] / "data" / "reports"
    return Path(os.getenv("REPORTS_DIR", default_path)).resolve()
