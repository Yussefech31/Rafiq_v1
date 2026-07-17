"""RAFIQ Evaluation Runner.

Reads eval/test_questions.csv, calls /api/ask for each question,
and reports key metrics:
  - Citation accuracy  (% with at least one valid source)
  - Abstention rate    (% with abstained=true)
  - Reuse rate         (% with regime=high)
  - Average confidence
  - Per-question results table

Usage:
    python -m eval.run_eval [--base-url http://localhost:8000]
"""

import csv
import json
import argparse
import sys
import time
from pathlib import Path
from urllib import request, error


# ── Configuration ────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://localhost:8000"
CSV_PATH = Path(__file__).parent / "test_questions.csv"


# ── Helpers ──────────────────────────────────────────────────────────────────

def call_ask(base_url: str, question: str, timeout: int = 30) -> dict:
    """POST a question to /api/ask and return the JSON response."""
    url = f"{base_url}/api/ask"
    payload = json.dumps({"question": question}).encode("utf-8")
    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"error": str(e)}


def print_separator(char: str = "─", width: int = 90):
    print(char * width)


def print_header(title: str):
    print()
    print_separator("═")
    print(f"  {title}")
    print_separator("═")
    print()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run RAFIQ evaluation suite.")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--csv",
        default=str(CSV_PATH),
        help=f"Path to test questions CSV (default: {CSV_PATH})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds between API calls (default: 0.5)",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        sys.exit(1)

    # Load questions
    questions = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(row)

    if not questions:
        print("ERROR: No questions found in CSV.")
        sys.exit(1)

    print_header(f"RAFIQ Evaluation — {len(questions)} questions")
    print(f"  API: {args.base_url}")
    print(f"  CSV: {csv_path}")
    print()

    # Run evaluation
    results = []
    for i, q in enumerate(questions, 1):
        question_text = q["question"].strip().strip('"')
        lang = q.get("language", "?")
        expected_source = q.get("expected_source", "")

        print(f"  [{i:2d}/{len(questions)}] ({lang}) {question_text[:60]}...", end=" ", flush=True)

        start = time.time()
        response = call_ask(args.base_url, question_text)
        elapsed = time.time() - start

        if "error" in response:
            print(f"✗ ERROR ({elapsed:.1f}s)")
            results.append({
                "question": question_text,
                "language": lang,
                "expected_source": expected_source,
                "error": response["error"],
                "answer": None,
                "confidence": None,
                "regime": None,
                "abstained": None,
                "has_sources": False,
                "elapsed": elapsed,
            })
        else:
            confidence = response.get("confidence", 0)
            regime = response.get("regime", "")
            abstained = response.get("abstained", False)
            sources = response.get("sources", [])
            has_sources = len(sources) > 0

            status = "✓" if not abstained else "⊘ ABSTAIN"
            print(f"{status} conf={confidence:.2f} regime={regime} ({elapsed:.1f}s)")

            results.append({
                "question": question_text,
                "language": lang,
                "expected_source": expected_source,
                "error": None,
                "answer": response.get("answer", ""),
                "confidence": confidence,
                "regime": regime,
                "abstained": abstained,
                "has_sources": has_sources,
                "elapsed": elapsed,
            })

        if args.delay > 0 and i < len(questions):
            time.sleep(args.delay)

    # ── Compute Metrics ──────────────────────────────────────────────────
    successful = [r for r in results if r["error"] is None]
    total = len(results)
    n_success = len(successful)
    n_errors = total - n_success

    if n_success > 0:
        citation_accuracy = sum(1 for r in successful if r["has_sources"]) / n_success * 100
        abstention_rate = sum(1 for r in successful if r["abstained"]) / n_success * 100
        reuse_rate = sum(1 for r in successful if r["regime"] == "high") / n_success * 100
        avg_confidence = sum(r["confidence"] for r in successful) / n_success
        avg_elapsed = sum(r["elapsed"] for r in successful) / n_success
    else:
        citation_accuracy = abstention_rate = reuse_rate = avg_confidence = avg_elapsed = 0

    # ── Print Report ─────────────────────────────────────────────────────
    print_header("Evaluation Results")

    print(f"  Total questions:      {total}")
    print(f"  Successful calls:     {n_success}")
    print(f"  Failed calls:         {n_errors}")
    print()
    print(f"  Citation accuracy:    {citation_accuracy:6.1f}%   (answers with ≥1 source)")
    print(f"  Abstention rate:      {abstention_rate:6.1f}%   (answers with abstained=true)")
    print(f"  Reuse rate:           {reuse_rate:6.1f}%   (answers with regime=high)")
    print(f"  Average confidence:   {avg_confidence:6.3f}")
    print(f"  Average latency:      {avg_elapsed:6.2f}s")
    print()

    # ── Per-question table ───────────────────────────────────────────────
    print_separator()
    header = f"{'#':>3}  {'Lang':>4}  {'Conf':>6}  {'Regime':>8}  {'Abs':>5}  {'Src':>3}  {'Time':>6}  Question"
    print(header)
    print_separator()

    for i, r in enumerate(results, 1):
        if r["error"]:
            print(f"{i:3d}  {r['language']:>4}  {'ERR':>6}  {'':>8}  {'':>5}  {'':>3}  {r['elapsed']:5.1f}s  {r['question'][:50]}")
        else:
            conf_str = f"{r['confidence']:.2f}" if r["confidence"] is not None else "—"
            abs_str = "YES" if r["abstained"] else "no"
            src_str = "✓" if r["has_sources"] else "✗"
            print(f"{i:3d}  {r['language']:>4}  {conf_str:>6}  {r['regime'] or '—':>8}  {abs_str:>5}  {src_str:>3}  {r['elapsed']:5.1f}s  {r['question'][:50]}")

    print_separator()
    print()

    # ── Save JSON report ─────────────────────────────────────────────────
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "base_url": args.base_url,
        "total_questions": total,
        "successful": n_success,
        "errors": n_errors,
        "metrics": {
            "citation_accuracy_pct": round(citation_accuracy, 2),
            "abstention_rate_pct": round(abstention_rate, 2),
            "reuse_rate_pct": round(reuse_rate, 2),
            "avg_confidence": round(avg_confidence, 4),
            "avg_latency_s": round(avg_elapsed, 3),
        },
        "results": results,
    }

    report_path = csv_path.parent / "eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"  Report saved to: {report_path}")
    print()


if __name__ == "__main__":
    main()
