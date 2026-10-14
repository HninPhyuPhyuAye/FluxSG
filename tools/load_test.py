import argparse
import json
import math
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(math.ceil(len(ordered) * fraction) - 1, len(ordered) - 1)
    return ordered[max(index, 0)]


def request_once(url: str, timeout: float) -> tuple[bool, float, int | None]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            response.read()
            status = response.status
        return 200 <= status < 400, time.perf_counter() - started, status
    except (urllib.error.URLError, TimeoutError):
        return False, time.perf_counter() - started, None


def run_load_test(
    *,
    url: str,
    requests: int,
    concurrency: int,
    timeout: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    results: list[tuple[bool, float, int | None]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(request_once, url, timeout) for _ in range(requests)]
        for future in as_completed(futures):
            results.append(future.result())
    duration = time.perf_counter() - started
    latencies = [latency for _, latency, _ in results]
    successes = sum(success for success, _, _ in results)
    status_counts: dict[str, int] = {}
    for _, _, status in results:
        label = str(status) if status is not None else "network_error"
        status_counts[label] = status_counts.get(label, 0) + 1
    success_rate = successes / requests
    p95 = percentile(latencies, 0.95)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "target": url,
        "requests": requests,
        "concurrency": concurrency,
        "duration_seconds": round(duration, 4),
        "requests_per_second": round(requests / duration, 2),
        "success_rate": round(success_rate, 4),
        "latency_seconds": {
            "p50": round(percentile(latencies, 0.50), 4),
            "p95": round(p95, 4),
            "p99": round(percentile(latencies, 0.99), 4),
            "max": round(max(latencies), 4),
        },
        "status_counts": status_counts,
        "thresholds": {
            "success_rate_at_least": 0.995,
            "p95_seconds_below": 0.75,
        },
        "passed": success_rate >= 0.995 and p95 < 0.75,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded FluxSG HTTP load test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--path", default="/health")
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=25)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--output", type=Path, default=Path("docs/evidence/load-test.json"))
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1 or args.concurrency > args.requests:
        parser.error("requests and concurrency must be positive; concurrency cannot exceed requests")
    url = f"{args.base_url.rstrip('/')}/{args.path.lstrip('/')}"
    report = run_load_test(
        url=url,
        requests=args.requests,
        concurrency=args.concurrency,
        timeout=args.timeout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
