"""Reproduce Exercise 3.5 retrieval-reranking measurements."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from template import RAGASEvaluator, rerank_by_overlap


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_reranking_report(
    golden_path: Path = Path("golden_dataset.json"),
    actual_path: Path = Path("artifacts/actual_answers.json"),
) -> list[dict[str, float | str]]:
    """Return before/after retrieval metrics for every recorded trace."""
    golden = _read_json(golden_path)["qa_pairs"]
    actual = _read_json(actual_path)["answers"]
    gold_by_id = {record["id"]: record for record in golden}
    evaluator = RAGASEvaluator()
    report: list[dict[str, float | str]] = []

    for record in actual:
        case_id = record["id"]
        pair = gold_by_id[case_id]
        contexts = [chunk["text"] for chunk in record["retrieved_contexts"]]
        reranked = rerank_by_overlap(contexts, pair["question"])
        recall_before = evaluator.evaluate_context_recall(
            contexts, pair["expected_answer"]
        )
        precision_before = evaluator.evaluate_context_precision(
            contexts, pair["expected_answer"]
        )
        recall_after = evaluator.evaluate_context_recall(
            reranked, pair["expected_answer"]
        )
        precision_after = evaluator.evaluate_context_precision(
            reranked, pair["expected_answer"]
        )
        report.append(
            {
                "id": case_id,
                "recall_before": recall_before,
                "recall_after": recall_after,
                "precision_before": precision_before,
                "precision_after": precision_after,
                "delta_precision": precision_after - precision_before,
            }
        )
    return report


def _print_markdown(rows: list[dict[str, float | str]], limit: int) -> None:
    selected = sorted(
        rows, key=lambda row: float(row["delta_precision"]), reverse=True
    )[:limit]
    print("| ID | Recall before | Recall after | Precision before | Precision after | Delta |")
    print("|---|---:|---:|---:|---:|---:|")
    for row in selected:
        print(
            f"| {row['id']} | {row['recall_before']:.3f} | "
            f"{row['recall_after']:.3f} | {row['precision_before']:.3f} | "
            f"{row['precision_after']:.3f} | {row['delta_precision']:+.3f} |"
        )
    if selected:
        keys = (
            "recall_before",
            "recall_after",
            "precision_before",
            "precision_after",
            "delta_precision",
        )
        averages = {
            key: sum(float(row[key]) for row in selected) / len(selected)
            for key in keys
        }
        print(
            f"| **Avg** | **{averages['recall_before']:.3f}** | "
            f"**{averages['recall_after']:.3f}** | "
            f"**{averages['precision_before']:.3f}** | "
            f"**{averages['precision_after']:.3f}** | "
            f"**{averages['delta_precision']:+.3f}** |"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=Path("golden_dataset.json"))
    parser.add_argument(
        "--actual", type=Path, default=Path("artifacts/actual_answers.json")
    )
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    _print_markdown(
        build_reranking_report(args.golden, args.actual), args.limit
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
