import json
import os
import time
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

import requests
from sqlalchemy import func

from database import SessionLocal, Disease, Stage, PainPoint, Solution, ChatbotFeedback

BASE_URL = os.getenv("PLATFORM_EVAL_BASE_URL", "http://127.0.0.1:8000")
OUT_DIR = Path("output") / "platform_eval"


def percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    idx = int(round((len(values_sorted) - 1) * q))
    idx = max(0, min(idx, len(values_sorted) - 1))
    return float(values_sorted[idx])


def count_files(folder: Path, pattern: str) -> int:
    if not folder.exists():
        return 0
    return len(list(folder.glob(pattern)))


def collect_frontend_metrics(project_root: Path) -> Dict[str, Any]:
    src = project_root / "frontend" / "disease-pathways" / "src"
    return {
        "component_count": count_files(src / "components", "*.jsx"),
        "page_count": count_files(src / "pages", "*.jsx"),
        "hook_count": count_files(src / "hooks", "*.js"),
        "util_count": count_files(src / "utils", "*.js"),
        "style_count": count_files(src / "styles", "*.css"),
    }


def collect_data_metrics() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        disease_count = db.query(func.count(Disease.id)).scalar() or 0
        stage_count = db.query(func.count(Stage.id)).scalar() or 0
        pain_point_count = db.query(func.count(PainPoint.id)).scalar() or 0
        solution_count = db.query(func.count(Solution.id)).scalar() or 0

        stages_with_stakeholders = (
            db.query(func.count(Stage.id))
            .filter(Stage.stakeholders.isnot(None))
            .filter(Stage.stakeholders != "")
            .scalar()
            or 0
        )

        pain_points_with_sources = (
            db.query(func.count(PainPoint.id))
            .filter(PainPoint.sources.isnot(None))
            .filter(PainPoint.sources != "")
            .scalar()
            or 0
        )

        pain_points_with_existing_solutions = (
            db.query(func.count(PainPoint.id))
            .filter(PainPoint.existing_solutions.isnot(None))
            .filter(PainPoint.existing_solutions != "")
            .scalar()
            or 0
        )

        viewed_pain_points = (
            db.query(func.count(PainPoint.id))
            .filter(PainPoint.view_count.isnot(None))
            .filter(PainPoint.view_count > 0)
            .scalar()
            or 0
        )

        feedback_total = db.query(func.count(ChatbotFeedback.id)).scalar() or 0
        feedback_up = (
            db.query(func.count(ChatbotFeedback.id))
            .filter(ChatbotFeedback.rating == 1)
            .scalar()
            or 0
        )
        feedback_down = (
            db.query(func.count(ChatbotFeedback.id))
            .filter(ChatbotFeedback.rating == -1)
            .scalar()
            or 0
        )

        return {
            "disease_count": disease_count,
            "stage_count": stage_count,
            "pain_point_count": pain_point_count,
            "solution_count": solution_count,
            "avg_stages_per_disease": round(stage_count / disease_count, 2) if disease_count else 0.0,
            "avg_pain_points_per_stage": round(pain_point_count / stage_count, 2) if stage_count else 0.0,
            "avg_solutions_per_pain_point": round(solution_count / pain_point_count, 2) if pain_point_count else 0.0,
            "stage_stakeholder_coverage": round(stages_with_stakeholders / stage_count, 4) if stage_count else 0.0,
            "pain_point_source_coverage": round(pain_points_with_sources / pain_point_count, 4) if pain_point_count else 0.0,
            "pain_point_existing_solution_coverage": round(
                pain_points_with_existing_solutions / pain_point_count, 4
            ) if pain_point_count else 0.0,
            "pain_points_with_views": viewed_pain_points,
            "pain_point_view_coverage": round(viewed_pain_points / pain_point_count, 4) if pain_point_count else 0.0,
            "feedback_total": feedback_total,
            "feedback_up": feedback_up,
            "feedback_down": feedback_down,
            "feedback_positive_rate": round(feedback_up / feedback_total, 4) if feedback_total else 0.0,
        }
    finally:
        db.close()


def timed_get(session: requests.Session, url: str) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        resp = session.get(url, timeout=30)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "url": url,
            "status": resp.status_code,
            "ok": 200 <= resp.status_code < 300,
            "latency_ms": round(elapsed_ms, 2),
            "size_bytes": len(resp.content or b""),
        }
    except Exception as ex:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "url": url,
            "status": None,
            "ok": False,
            "latency_ms": round(elapsed_ms, 2),
            "error": str(ex),
            "size_bytes": 0,
        }


def collect_api_metrics() -> Dict[str, Any]:
    session = requests.Session()
    core_endpoints = [
        f"{BASE_URL}/health",
        f"{BASE_URL}/diseases",
        f"{BASE_URL}/stats",
        f"{BASE_URL}/analytics/summary",
        f"{BASE_URL}/trending?limit=5",
    ]

    endpoint_results = [timed_get(session, url) for url in core_endpoints]

    diseases = []
    try:
        diseases_resp = session.get(f"{BASE_URL}/diseases", timeout=30)
        if diseases_resp.ok:
            diseases = diseases_resp.json()
    except Exception:
        diseases = []

    feature_results = []
    for d in diseases:
        name = d.get("name", "")
        if not name:
            continue
        encoded = requests.utils.quote(name, safe="")
        feature_results.append(timed_get(session, f"{BASE_URL}/diseases/{encoded}"))
        feature_results.append(timed_get(session, f"{BASE_URL}/diseases/{encoded}/pathway"))
        feature_results.append(timed_get(session, f"{BASE_URL}/diseases/{encoded}/similar?top_k=3"))

    # Search smoke checks from canonical disease intents.
    search_payloads = [
        {"query": "pain points in diagnosis", "disease_name": "lung cancer staging", "k": 5},
        {"query": "key cardiology pain points", "disease_name": "cad", "k": 5},
        {"query": "memory care pain points", "disease_name": "alzheimer's", "k": 5},
    ]
    search_results = []
    for payload in search_payloads:
        start = time.perf_counter()
        try:
            r = session.post(f"{BASE_URL}/search", json=payload, timeout=60)
            elapsed = (time.perf_counter() - start) * 1000
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            count = len(body.get("results", [])) if isinstance(body, dict) else 0
            search_results.append({
                "query": payload["query"],
                "status": r.status_code,
                "ok": 200 <= r.status_code < 300,
                "latency_ms": round(elapsed, 2),
                "result_count": count,
            })
        except Exception as ex:
            elapsed = (time.perf_counter() - start) * 1000
            search_results.append({
                "query": payload["query"],
                "status": None,
                "ok": False,
                "latency_ms": round(elapsed, 2),
                "result_count": 0,
                "error": str(ex),
            })

    all_results = endpoint_results + feature_results
    latencies = [r["latency_ms"] for r in all_results if r.get("ok")]
    ok_count = sum(1 for r in all_results if r.get("ok"))
    total_count = len(all_results)

    search_ok = sum(1 for r in search_results if r.get("ok"))
    search_non_empty = sum(1 for r in search_results if r.get("result_count", 0) > 0)

    return {
        "core_endpoint_checks": endpoint_results,
        "disease_feature_checks": feature_results,
        "search_checks": search_results,
        "api_success_rate": round(ok_count / total_count, 4) if total_count else 0.0,
        "api_avg_latency_ms": round(mean(latencies), 2) if latencies else 0.0,
        "api_p95_latency_ms": round(percentile(latencies, 0.95), 2) if latencies else 0.0,
        "api_checked_routes": total_count,
        "search_success_rate": round(search_ok / len(search_results), 4) if search_results else 0.0,
        "search_non_empty_rate": round(search_non_empty / len(search_results), 4) if search_results else 0.0,
        "validated_disease_count": len(diseases),
    }


def build_markdown_report(result: Dict[str, Any]) -> str:
    frontend = result.get("frontend_metrics", {})
    data = result.get("data_metrics", {})
    api = result.get("api_metrics", {})

    lines = [
        "# Platform Evaluation Report",
        "",
        f"- Generated: {result.get('generated_at')}",
        "",
        "## Frontend Complexity",
        f"- Components: {frontend.get('component_count')}",
        f"- Pages: {frontend.get('page_count')}",
        f"- Hooks: {frontend.get('hook_count')}",
        f"- Utils: {frontend.get('util_count')}",
        f"- Styles: {frontend.get('style_count')}",
        "",
        "## Data Quality & Coverage",
        f"- Diseases: {data.get('disease_count')}",
        f"- Stages: {data.get('stage_count')}",
        f"- Pain Points: {data.get('pain_point_count')}",
        f"- Solutions: {data.get('solution_count')}",
        f"- Avg Stages/Disease: {data.get('avg_stages_per_disease')}",
        f"- Avg Pain Points/Stage: {data.get('avg_pain_points_per_stage')}",
        f"- Avg Solutions/Pain Point: {data.get('avg_solutions_per_pain_point')}",
        f"- Stakeholder Coverage: {data.get('stage_stakeholder_coverage')}",
        f"- Source Coverage: {data.get('pain_point_source_coverage')}",
        f"- Existing-Solution Coverage: {data.get('pain_point_existing_solution_coverage')}",
        "",
        "## Runtime API Reliability",
        f"- Checked Routes: {api.get('api_checked_routes')}",
        f"- API Success Rate: {api.get('api_success_rate')}",
        f"- API Avg Latency (ms): {api.get('api_avg_latency_ms')}",
        f"- API P95 Latency (ms): {api.get('api_p95_latency_ms')}",
        f"- Search Success Rate: {api.get('search_success_rate')}",
        f"- Search Non-Empty Rate: {api.get('search_non_empty_rate')}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    project_root = Path(__file__).resolve().parent

    result = {
        "generated_at": datetime.now().isoformat(),
        "frontend_metrics": collect_frontend_metrics(project_root),
        "data_metrics": collect_data_metrics(),
        "api_metrics": collect_api_metrics(),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_file = OUT_DIR / f"platform_eval_{ts}.json"
    md_file = OUT_DIR / f"platform_eval_{ts}.md"

    json_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    md_file.write_text(build_markdown_report(result), encoding="utf-8")

    print("JSON_REPORT", json_file.as_posix())
    print("MD_REPORT", md_file.as_posix())
    print("API_SUCCESS_RATE", result["api_metrics"].get("api_success_rate"))
    print("API_P95_MS", result["api_metrics"].get("api_p95_latency_ms"))
    print("SEARCH_NON_EMPTY_RATE", result["api_metrics"].get("search_non_empty_rate"))


if __name__ == "__main__":
    main()
