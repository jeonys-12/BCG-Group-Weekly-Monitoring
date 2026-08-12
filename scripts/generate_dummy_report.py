"""Generate the Phase 1 dummy report from the approved master template."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.excel_writer import append_trends, load_rules


def main() -> None:
    template = ROOT / "reports/template/BCG_Group_Trend_Master.xlsx"
    if not template.exists():
        raise SystemExit(
            "Missing reports/template/BCG_Group_Trend_Master.xlsx. "
            "Provide the approved master; no synthetic production template will be generated."
        )
    items = json.loads((ROOT / "tests/fixtures/dummy_items.json").read_text(encoding="utf-8"))
    output = ROOT / "reports/output/BCG_Group_Trend_Phase1_Dummy.xlsx"
    append_trends(
        template,
        output,
        items,
        load_rules(ROOT / "config/report_rules.yaml"),
        report_start=date(2026, 8, 12),
        report_end=date(2026, 8, 19),
    )
    print(output)


if __name__ == "__main__":
    main()
