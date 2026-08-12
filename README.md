# BCG Group Weekly Monitoring Automation

The project provides a conservative append-only Excel report engine and official BCG/BCG Land investor-relations collectors. A local Windows Task Scheduler workflow connects the approved collectors to the approved `.xlsx` Master and saves a new weekly report without overwriting the template or an earlier output.

HNX, HOSE, and SSC are not monitored. Their existing institution-description rows remain in the workbook only as protected layout content. The current workflow does not classify, translate, generate summaries, or write impact conclusions. It uses the official source title and preserves the source URL as a hyperlink.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Collect official disclosures

```powershell
.\.venv\Scripts\python.exe -m src.main `
  --config config/sources.yaml `
  --start 2026-08-06 `
  --end 2026-08-07 `
  --max-pages 1 `
  --output data/processed/2026-08-07.json
```

The CLI writes normalized JSON and archives every live response under the configured `archive_root`. A parser or network failure is reported as `PARTIAL` or `FAILED`; it is never converted into a successful empty result.

## Generate a weekly Excel report manually

The default window is the last fully completed Monday through Sunday. For example, a run on Monday 2026-08-10 or Wednesday 2026-08-12 covers 2026-08-03 through 2026-08-09.

```powershell
.\scripts\run_weekly.ps1 `
  -OutputFolder "C:\Users\User\Documents\BCG Weekly Reports"
```

Use `-RunDate yyyy-MM-dd` only for a reproducible backfill or test. Successful source checks with zero disclosures still produce a dated workbook. If every configured source fails, the workflow writes audit metadata and a log but does not create a workbook.

## Install the Monday Windows scheduled task

```powershell
.\scripts\install_weekly_task.ps1 `
  -OutputFolder "C:\Users\User\Documents\BCG Weekly Reports" `
  -At "07:00"
```

The default task runs every Monday at 07:00 for the current Windows user while that user is signed in. It starts as soon as possible after a missed start, prevents overlapping runs, can wake the computer, and stops after two hours. To run while signed out, reinstall with `-RunWhetherLoggedOn`; Windows will securely prompt for the account credential.

Inspect or test the task:

```powershell
Get-ScheduledTask -TaskName "BCG Group Weekly Monitoring"
Start-ScheduledTask -TaskName "BCG Group Weekly Monitoring"
Get-ScheduledTaskInfo -TaskName "BCG Group Weekly Monitoring"
```

Remove it with:

```powershell
.\scripts\uninstall_weekly_task.ps1
```

Generated workbooks go to the selected output folder. Run logs go to `logs/`, raw source archives to `data/raw/`, and weekly audit metadata to `data/history/`. These runtime artifacts are excluded from Git.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

All default tests use local fixtures and make no live network calls. To run the explicitly separated bounded live smoke test:

```powershell
$env:RUN_LIVE_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest -m integration -q
```

## Excel safety

The approved Master is `reports/template/BCG_Group_Trend_Master.xlsx`. The writer never overwrites it. The source XLSB is analysis-only because Python libraries cannot safely round-trip its binary workbook structure and SoftCamp DRM envelope. See `docs/design.md` for the conversion and validation rationale.