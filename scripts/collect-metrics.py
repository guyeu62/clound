#!/usr/bin/env python3
"""
Script thu thập metrics từ Prometheus API để lưu ra CSV/JSON
Cách chạy:
  kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090
  python scripts/collect-metrics.py --scenario baseline --output data/results/baseline.json
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime

# Dam bao terminal Windows khong bi loi Unicode charmap
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

QUERIES = {
    "request_rate": 'sum(rate(http_requests_total[1m]))',
    "latency_p95": 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))',
    "error_rate_5xx": 'sum(rate(http_requests_total{status=~"5.."}[1m])) or vector(0)',
    "pod_restarts": 'sum(kube_pod_container_status_restarts_total{pod=~"selfhealing-demo.*"}) or vector(0)',
    "replicas_available": 'kube_deployment_status_replicas_available{deployment="selfhealing-demo"} or vector(0)'
}

def query_prometheus(query: str):
    params = urllib.parse.urlencode({'query': query})
    url = f"{PROMETHEUS_URL}/api/v1/query?{params}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "success":
                results = data["data"]["result"]
                if results:
                    return float(results[0]["value"][1])
                return 0.0
    except Exception as e:
        print(f"[WARN] Lỗi khi query PromQL '{query}': {e}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Thu thập số liệu đo từ Prometheus")
    parser.add_argument("--scenario", required=True, help="Tên kịch bản (ví dụ: baseline, delete-pod, drain, rollout-fail, hpa)")
    parser.add_argument("--output", default=None, help="Đường dẫn file lưu kết quả JSON")
    args = parser.parse_args()

    timestamp = datetime.now().isoformat()
    metrics = {
        "scenario": args.scenario,
        "timestamp": timestamp,
        "data": {}
    }

    print(f"[*] Đang thu thập số liệu cho kịch bản: {args.scenario}...")
    for name, query in QUERIES.items():
        val = query_prometheus(query)
        metrics["data"][name] = val
        print(f"  - {name}: {val}")

    output_path = args.output or f"data/results/{args.scenario}_{int(datetime.now().timestamp())}.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"[+] Đã lưu kết quả đo vào: {output_path}")

if __name__ == "__main__":
    main()

