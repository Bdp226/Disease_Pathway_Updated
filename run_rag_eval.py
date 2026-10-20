import json
from datetime import datetime
from pathlib import Path

import requests


API_URL = "http://127.0.0.1:8000/rag/evaluate"
OUTPUT_DIR = Path("output") / "rag_eval"


def main() -> None:
    payload = {
        "k": 5,
        "max_cases_per_disease": 10,
    }

    response = requests.post(API_URL, json=payload, timeout=120)
    response.raise_for_status()

    result = response.json()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"rag_eval_{ts}.json"
    report_file = OUTPUT_DIR / f"rag_eval_{ts}.md"

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    summary = result.get("summary", {})
    baseline = result.get("baseline_summary") or {}
    delta = result.get("improvement_delta") or {}

    report_lines = [
        "# RAG Evaluation Report",
        "",
        f"- Generated: {datetime.now().isoformat()}",
        f"- Benchmark Queries: {result.get('benchmark_queries')}",
        f"- Evaluated Diseases: {', '.join(result.get('evaluated_diseases', []))}",
        f"- Auto Indexed Diseases: {', '.join(result.get('auto_indexed_diseases', []))}",
        "",
        "## Hybrid RAG Metrics",
        f"- Hit@k: {summary.get('hit_rate_at_k')}",
        f"- Precision@k: {summary.get('precision_at_k')}",
        f"- Recall@k: {summary.get('recall_at_k')}",
        f"- MRR: {summary.get('mrr')}",
        f"- Avg Latency (ms): {summary.get('avg_latency_ms')}",
        f"- P95 Latency (ms): {summary.get('p95_latency_ms')}",
        "",
    ]

    if baseline:
        report_lines.extend([
            "## Baseline (Semantic-only) Metrics",
            f"- Hit@k: {baseline.get('hit_rate_at_k')}",
            f"- Precision@k: {baseline.get('precision_at_k')}",
            f"- Recall@k: {baseline.get('recall_at_k')}",
            f"- MRR: {baseline.get('mrr')}",
            f"- Avg Latency (ms): {baseline.get('avg_latency_ms')}",
            f"- P95 Latency (ms): {baseline.get('p95_latency_ms')}",
            "",
            "## Hybrid vs Baseline Delta",
            f"- Delta Hit@k: {delta.get('delta_hit_rate_at_k')}",
            f"- Delta Precision@k: {delta.get('delta_precision_at_k')}",
            f"- Delta Recall@k: {delta.get('delta_recall_at_k')}",
            f"- Delta MRR: {delta.get('delta_mrr')}",
            f"- Delta Avg Latency (ms): {delta.get('delta_avg_latency_ms')}",
            "",
        ])

    report_file.write_text("\n".join(report_lines), encoding="utf-8")

    print("Saved:", output_file)
    print("Report:", report_file)
    print("benchmark_queries:", result.get("benchmark_queries"))
    print("evaluated_diseases:", ", ".join(result.get("evaluated_diseases", [])))
    print("hit_rate_at_k:", summary.get("hit_rate_at_k"))
    print("precision_at_k:", summary.get("precision_at_k"))
    print("recall_at_k:", summary.get("recall_at_k"))
    print("mrr:", summary.get("mrr"))
    print("avg_latency_ms:", summary.get("avg_latency_ms"))
    print("p95_latency_ms:", summary.get("p95_latency_ms"))


if __name__ == "__main__":
    main()
