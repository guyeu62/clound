#!/usr/bin/env python3
"""
Script doc du lieu tu data/results/*.json va ve bieu do ket qua
Yeu cau: pip install matplotlib
Cach chay:
  python scripts/plot-results.py
"""

import os
import sys
import tempfile

# Set thu muc cache ghi duoc cho matplotlib tren Windows
os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())

# Dam bao terminal Windows khong bi loi Unicode charmap
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import glob
import json
import matplotlib.pyplot as plt

DATA_DIR = "data/results"
OUTPUT_DIR = "docs/results"

def load_data():
    results = {}
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                scenario = content.get("scenario", os.path.basename(file_path))
                results[scenario] = content.get("data", {})
        except Exception as e:
            print(f"[WARN] Error reading {file_path}: {e}")
    return results

def plot_metrics(results):
    if not results:
        print("[INFO] No JSON data found in data/results/ yet. Run test scenarios first.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    scenarios = list(results.keys())

    # 1. Bieu do Latency p95
    p95_values = [results[s].get("latency_p95", 0) * 1000 for s in scenarios]  # ms
    plt.figure(figsize=(10, 5))
    bars = plt.bar(scenarios, p95_values, color="#3498db")
    plt.title("Latency p95 Comparison Across Scenarios (ms)")
    plt.ylabel("Latency p95 (ms)")
    plt.xticks(rotation=20)
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f"{yval:.1f} ms", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "latency_p95_comparison.png"))
    plt.close()

    # 2. Bieu do Ty le loi 5xx
    error_values = [results[s].get("error_rate_5xx", 0) for s in scenarios]
    plt.figure(figsize=(10, 5))
    bars = plt.bar(scenarios, error_values, color="#e74c3c")
    plt.title("5xx Error Rate Comparison Across Scenarios (req/s)")
    plt.ylabel("5xx Errors / sec")
    plt.xticks(rotation=20)
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f"{yval:.2f}", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "error_rate_comparison.png"))
    plt.close()

    print(f"[SUCCESS] Exported result charts to: {OUTPUT_DIR}")

if __name__ == "__main__":
    data = load_data()
    plot_metrics(data)
