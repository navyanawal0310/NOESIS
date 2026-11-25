"""Statistical Analysis Script for NIC-50 Human Validation Study.

Processes completed human subject records or reports pending protocol readiness
without fabricating participants or results.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from typing import Any, Dict

STUDY_DIR = Path(__file__).resolve().parent
RESULTS_FILE = STUDY_DIR / "results.csv"
TEMPLATE_FILE = STUDY_DIR / "results_template.csv"
OUTPUT_SUMMARY = STUDY_DIR / "summary.json"


def analyze_human_study() -> Dict[str, Any]:
    print("=" * 65)
    print("NOESIS NIC-50 HUMAN VALIDATION STUDY ANALYSIS")
    print("=" * 65)

    target_file = RESULTS_FILE if RESULTS_FILE.exists() else TEMPLATE_FILE
    if not target_file.exists():
        print("ERROR: Neither results.csv nor results_template.csv found.")
        return {"status": "error", "message": "Missing study files"}

    with open(target_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Check if rows contain completed data
    completed_rows = [
        r for r in rows
        if r.get("completed") is not None and r.get("completed").strip() != ""
    ]

    if not completed_rows:
        print("\nSTATUS: Pending experimental execution with human subjects.")
        print("Protocol, tasks (10), consent form, and trial matrix (50 runs) fully configured.")
        print("Adhering strictly to research ethics: Zero fabricated participants or results.\n")

        pending_report = {
            "status": "pending_human_execution",
            "study_name": "NIC-50",
            "participants_planned": 5,
            "tasks_per_participant": 10,
            "total_planned_trials": 50,
            "conditions": ["noesis_assisted", "manual_unassisted"],
            "protocol_file": str(STUDY_DIR / "protocol.md"),
            "tasks_file": str(STUDY_DIR / "tasks.json"),
            "template_file": str(TEMPLATE_FILE),
            "results_collected": 0,
        }
        with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as sf:
            json.dump(pending_report, sf, indent=2)

        print("=" * 65)
        print(f"Summary status recorded to: {OUTPUT_SUMMARY}\n")
        return pending_report

    # If completed rows exist, process statistics
    noesis_times = []
    manual_times = []
    noesis_acc = []
    manual_acc = []

    for r in completed_rows:
        sys_used = r["system_used"].strip().lower()
        try:
            t = float(r["time_seconds"])
            acc = float(r["accuracy"])
            if sys_used == "noesis":
                noesis_times.append(t)
                noesis_acc.append(acc)
            else:
                manual_times.append(t)
                manual_acc.append(acc)
        except ValueError:
            continue

    summary: Dict[str, Any] = {
        "status": "completed",
        "total_trials_analyzed": len(completed_rows),
        "noesis": {
            "trials": len(noesis_times),
            "mean_time_seconds": round(statistics.mean(noesis_times), 2) if noesis_times else 0.0,
            "accuracy": round(statistics.mean(noesis_acc), 4) if noesis_acc else 0.0,
        },
        "manual": {
            "trials": len(manual_times),
            "mean_time_seconds": round(statistics.mean(manual_times), 2) if manual_times else 0.0,
            "accuracy": round(statistics.mean(manual_acc), 4) if manual_acc else 0.0,
        },
    }

    if manual_times and noesis_times:
        speedup = statistics.mean(manual_times) / max(statistics.mean(noesis_times), 0.001)
        summary["speedup_factor"] = round(speedup, 2)

    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as sf:
        json.dump(summary, sf, indent=2)

    print("Analysis complete. Saved to:", OUTPUT_SUMMARY)
    return summary


if __name__ == "__main__":
    analyze_human_study()
