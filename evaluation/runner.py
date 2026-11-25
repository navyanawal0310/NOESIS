"""Resumable Benchmark Runner for NOESIS Scientific Evaluation."""

from __future__ import annotations

import csv
import json
import logging
import platform
import time
from pathlib import Path
from typing import Any, Dict, List

from evaluation.baselines import (
    BaselineExecutionResult,
    BaseReasoningSystem,
    ConventionalRAGSystem,
    FullNOESISSystem,
    NOESISWithoutEAQCSystem,
    StandardKGSystem,
)
from evaluation.metrics import (
    abstention_accuracy,
    answer_exact_match,
    complete_query_plan_accuracy,
    compute_benchmark_summary,
    contradiction_precision,
    contradiction_recall,
    end_to_end_latency,
    entity_set_f1,
    entity_set_precision,
    entity_set_recall,
    graph_traversal_latency,
    llm_calls_per_query,
    planning_latency,
    predicate_sequence_accuracy,
    reasoning_path_validity,
    start_entity_accuracy,
    traversal_direction_accuracy,
    unsupported_constraint_handling,
)
from evaluation.schemas import CaseExecutionRecord, ExperimentConfig, ExperimentSummary

logger = logging.getLogger("noesis.evaluation.runner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT_DIR = Path(__file__).resolve().parent.parent
BENCHMARK_PATH = ROOT_DIR / "datasets" / "benchmarks" / "nvs100.json"
RESULTS_DIR = ROOT_DIR / "evaluation" / "results"


def get_hardware_info() -> Dict[str, Any]:
    """Capture runtime device specifications for reproducible logging."""
    return {
        "os": platform.system(),
        "release": platform.release(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "machine": platform.machine(),
    }


def instantiate_system(system_name: str) -> BaseReasoningSystem:
    """Factory creating benchmark baseline instance."""
    name_norm = system_name.strip().lower()
    if name_norm == "noesis":
        return FullNOESISSystem()
    elif name_norm in ["noesis_no_eaqc", "noesis-no-eaqc"]:
        return NOESISWithoutEAQCSystem()
    elif name_norm in ["standard_kg", "standard-kg"]:
        return StandardKGSystem()
    elif name_norm == "rag":
        return ConventionalRAGSystem()
    else:
        raise ValueError(f"Unknown system name: '{system_name}'")


class BenchmarkRunner:
    """Orchestrates scientific evaluation runs over NVS-100."""

    def __init__(self, config: ExperimentConfig):
        self.config = config
        self.output_dir = RESULTS_DIR / config.experiment_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.results_json_path = self.output_dir / "results.json"
        self.results_csv_path = self.output_dir / "results.csv"
        self.summary_json_path = self.output_dir / "summary.json"
        self.metadata_json_path = self.output_dir / "metadata.json"

        self.system = instantiate_system(config.system_name)

        if config.cache_policy == "clear_cache":
            try:
                from backend.app.reasoning.nl_planner import clear_cache
                clear_cache()
                logger.info("Cleared in-memory NL query plan cache.")
            except Exception:
                pass

    def _load_benchmark_cases(self) -> List[Dict[str, Any]]:
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            cases: List[Dict[str, Any]] = json.load(f)

        filtered = []
        for c in cases:
            # Filter split
            if self.config.split != "all" and c.get("split") != self.config.split:
                continue
            # Filter category
            if self.config.category != "all" and c.get("category") != self.config.category:
                continue
            filtered.append(c)

        if self.config.limit is not None and self.config.limit > 0:
            filtered = filtered[: self.config.limit]

        return filtered

    def _load_existing_results(self) -> Dict[str, CaseExecutionRecord]:
        """Loads prior results if resuming."""
        if not self.config.resume or not self.results_json_path.exists():
            return {}

        existing: Dict[str, CaseExecutionRecord] = {}
        try:
            with open(self.results_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    rec = CaseExecutionRecord(**item)
                    existing[rec.case_id] = rec
            logger.info("Resuming experiment '%s': loaded %d existing records.", self.config.experiment_id, len(existing))
        except Exception as e:
            logger.warning("Could not load existing results for resume: %s", e)
        return existing

    def _evaluate_case(self, case: Dict[str, Any]) -> CaseExecutionRecord:
        """Executes a single benchmark case and evaluates metrics."""
        case_id = case["case_id"]
        question = case["question"]
        expected_entities = case.get("expected_answer_entities", [])
        expected_paths = case.get("expected_reasoning_paths", [])
        expected_predicates = case.get("expected_predicates", [])
        expected_directions = case.get("expected_directions", [])
        expected_contradiction = case.get("expected_contradiction_status", False)
        expected_abstention = case.get("expected_abstention_status", False)
        sqp = case.get("structured_query_plan")

        exec_res: BaselineExecutionResult = self.system.execute(
            question=question,
            case_id=case_id,
            structured_plan=sqp,
            mode=self.config.mode,
        )

        # Compute Core Metrics
        em_res = answer_exact_match(exec_res.answer_entities, expected_entities)
        p_res = entity_set_precision(exec_res.answer_entities, expected_entities)
        r_res = entity_set_recall(exec_res.answer_entities, expected_entities)
        f1_res = entity_set_f1(exec_res.answer_entities, expected_entities)
        path_res = reasoning_path_validity(exec_res.reasoning_paths, expected_paths)

        # Planning Metrics
        gold_start = sqp.get("start_entity", "") if sqp else ""
        pred_start = exec_res.metadata.get("plan_start_entity", "") or exec_res.metadata.get("unconstrained_start_entity", "")
        start_res = start_entity_accuracy(pred_start, gold_start) if gold_start else None
        pred_seq_res = predicate_sequence_accuracy(exec_res.predicates, expected_predicates) if expected_predicates else None
        dir_res = traversal_direction_accuracy(exec_res.directions, expected_directions) if expected_directions else None
        plan_res = (
            complete_query_plan_accuracy(
                pred_start, exec_res.predicates, exec_res.directions,
                gold_start, expected_predicates, expected_directions,
            )
            if gold_start and expected_predicates and expected_directions
            else None
        )

        # Dialectical Metrics
        is_contra_tp = (exec_res.contradiction_detected and expected_contradiction)
        contra_p = contradiction_precision(1 if is_contra_tp else 0, 1 if exec_res.contradiction_detected else 0)
        contra_r = contradiction_recall(1 if is_contra_tp else 0, 1 if expected_contradiction else 0)
        abs_res = abstention_accuracy(exec_res.abstained, expected_abstention)

        unsupported_res = None
        if sqp and sqp.get("temporal_constraint") in ["1850", "unsupported"]:
            unsupported_res = unsupported_constraint_handling(1 if exec_res.abstained else 0, 1)

        metrics_map = {
            "answer_exact_match": em_res.to_dict(),
            "entity_set_precision": p_res.to_dict(),
            "entity_set_recall": r_res.to_dict(),
            "entity_set_f1": f1_res.to_dict(),
            "reasoning_path_validity": path_res.to_dict(),
            "abstention_accuracy": abs_res.to_dict(),
            "end_to_end_latency": end_to_end_latency(exec_res.latency_ms).to_dict(),
            "graph_traversal_latency": graph_traversal_latency(exec_res.graph_traversal_ms).to_dict(),
            "planning_latency": planning_latency(exec_res.planning_ms).to_dict(),
            "llm_calls_per_query": llm_calls_per_query(exec_res.llm_calls).to_dict(),
        }

        if start_res:
            metrics_map["start_entity_accuracy"] = start_res.to_dict()
        if pred_seq_res:
            metrics_map["predicate_sequence_accuracy"] = pred_seq_res.to_dict()
        if dir_res:
            metrics_map["traversal_direction_accuracy"] = dir_res.to_dict()
        if plan_res:
            metrics_map["complete_query_plan_accuracy"] = plan_res.to_dict()
        if unsupported_res:
            metrics_map["unsupported_constraint_handling"] = unsupported_res.to_dict()
        if expected_contradiction or exec_res.contradiction_detected:
            metrics_map["contradiction_precision"] = contra_p.to_dict()
            metrics_map["contradiction_recall"] = contra_r.to_dict()

        return CaseExecutionRecord(
            case_id=case_id,
            system_name=self.config.system_name,
            question=question,
            category=case.get("category", "unknown"),
            difficulty=case.get("difficulty", "medium"),
            split=case.get("split", "dev"),
            predicted_entities=exec_res.answer_entities,
            expected_entities=expected_entities,
            is_exact_match=bool(em_res.value == 1.0),
            precision=p_res.value,
            recall=r_res.value,
            f1=f1_res.value,
            executed_paths=exec_res.reasoning_paths,
            expected_paths=expected_paths,
            citations=exec_res.citations,
            expected_evidence=case.get("expected_evidence", []),
            contradiction_detected=exec_res.contradiction_detected,
            expected_contradiction=expected_contradiction,
            abstained=exec_res.abstained,
            expected_abstention=expected_abstention,
            latency_ms=exec_res.latency_ms,
            graph_traversal_ms=exec_res.graph_traversal_ms,
            planning_ms=exec_res.planning_ms,
            llm_calls=exec_res.llm_calls,
            raw_response=exec_res.raw_response,
            metrics=metrics_map,
        )

    def _persist_incremental(self, records: List[CaseExecutionRecord]) -> None:
        """Saves current state to JSON and CSV after each completed case."""
        # 1. JSON Export
        data = [r.model_dump() for r in records]
        with open(self.results_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # 2. CSV Export
        if records:
            fieldnames = [
                "case_id", "system_name", "category", "split", "difficulty",
                "is_exact_match", "precision", "recall", "f1",
                "predicted_entities", "expected_entities",
                "contradiction_detected", "expected_contradiction",
                "abstained", "expected_abstention",
                "latency_ms", "graph_traversal_ms", "planning_ms", "llm_calls",
            ]
            with open(self.results_csv_path, "w", newline="", encoding="utf-8") as cf:
                writer = csv.DictWriter(cf, fieldnames=fieldnames)
                writer.writeheader()
                for r in records:
                    writer.writerow({
                        "case_id": r.case_id,
                        "system_name": r.system_name,
                        "category": r.category,
                        "split": r.split,
                        "difficulty": r.difficulty,
                        "is_exact_match": r.is_exact_match,
                        "precision": round(r.precision, 4),
                        "recall": round(r.recall, 4),
                        "f1": round(r.f1, 4),
                        "predicted_entities": "; ".join(r.predicted_entities),
                        "expected_entities": "; ".join(r.expected_entities),
                        "contradiction_detected": r.contradiction_detected,
                        "expected_contradiction": r.expected_contradiction,
                        "abstained": r.abstained,
                        "expected_abstention": r.expected_abstention,
                        "latency_ms": round(r.latency_ms, 2),
                        "graph_traversal_ms": round(r.graph_traversal_ms, 2),
                        "planning_ms": round(r.planning_ms, 2),
                        "llm_calls": r.llm_calls,
                    })

    def run(self) -> ExperimentSummary:
        """Executes full experiment run and returns comprehensive summary."""
        start_time = time.perf_counter()
        cases = self._load_benchmark_cases()
        existing_records = self._load_existing_results()

        records: List[CaseExecutionRecord] = list(existing_records.values())
        completed_ids = set(existing_records.keys())

        logger.info(
            "Starting Experiment '%s' [System=%s, Mode=%s, Split=%s, Category=%s, Total Cases=%d, Already Done=%d]",
            self.config.experiment_id, self.config.system_name, self.config.mode,
            self.config.split, self.config.category, len(cases), len(completed_ids),
        )

        failed_count = 0

        for idx, case in enumerate(cases):
            cid = case["case_id"]
            if cid in completed_ids:
                continue

            try:
                rec = self._evaluate_case(case)
                records.append(rec)
                self._persist_incremental(records)
                logger.info(
                    "[%d/%d] Case %s (%s) -> EM=%s, F1=%.2f, Latency=%.1fms",
                    idx + 1, len(cases), cid, case["category"],
                    rec.is_exact_match, rec.f1, rec.latency_ms,
                )
            except Exception as e:
                logger.error("Error executing case %s: %s", cid, e, exc_info=True)
                failed_count += 1

        total_duration = time.perf_counter() - start_time

        # Compute consolidated metrics
        summary_dict = compute_benchmark_summary([r.model_dump() for r in records])

        summary = ExperimentSummary(
            experiment_id=self.config.experiment_id,
            config=self.config,
            total_cases=len(cases),
            completed_cases=len(records),
            failed_cases=failed_count,
            duration_seconds=round(total_duration, 2),
            metrics=summary_dict.get("metrics", {}),
        )

        # Write summary.json and metadata.json
        with open(self.summary_json_path, "w", encoding="utf-8") as sf:
            json.dump(summary.model_dump(), sf, indent=2)

        metadata_payload = {
            "config": self.config.model_dump(),
            "device_info": get_hardware_info(),
            "generated_at": summary.completed_at,
            "results_files": {
                "results_json": str(self.results_json_path.name),
                "results_csv": str(self.results_csv_path.name),
                "summary_json": str(self.summary_json_path.name),
            },
        }
        with open(self.metadata_json_path, "w", encoding="utf-8") as mf:
            json.dump(metadata_payload, mf, indent=2)

        logger.info(
            "Experiment '%s' completed successfully in %.2fs. Exports available in %s",
            self.config.experiment_id, total_duration, self.output_dir,
        )
        return summary
