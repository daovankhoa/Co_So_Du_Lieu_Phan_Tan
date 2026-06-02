"""
run_cluster.py
==============
Script tiện ích để khởi động toàn bộ cluster chỉ bằng 1 lệnh.

Khởi động:
  python run_cluster.py

Hệ thống sẽ:
  1. Chạy main.py để sinh data + tạo shard files
  2. Khởi động 3 Shard Node (port 5001, 5002, 5003) — mỗi cái 1 process
  3. Khởi động Coordinator (port 5000)
  4. Tự động gọi /detect sau 2 giây và in kết quả

Dừng: Ctrl+C
"""

import subprocess
import sys
import os
import time
import json
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON   = sys.executable

SHARD_CONFIGS = [
    {"shard": 0, "port": 5001},
    {"shard": 1, "port": 5002},
    {"shard": 2, "port": 5003},
]
COORDINATOR_PORT = 5000


def wait_for_port(port: int, retries: int = 10, delay: float = 0.5) -> bool:
    """Chờ cho đến khi server tại port sẵn sàng."""
    for _ in range(retries):
        try:
            urllib.request.urlopen(f"http://localhost:{port}/status", timeout=1)
            return True
        except Exception:
            time.sleep(delay)
    return False


def main():
    processes = []

    print("\n" + "█" * 55)
    print("  Starting Fraud Ring Detection Cluster")
    print("█" * 55)

    # ── Bước 1: Sinh data và tạo shard files ──────────────────
    print("\n[1/4] Generating data and shard files...")
    result = subprocess.run(
        [PYTHON, os.path.join(BASE_DIR, "main.py")],
        cwd=BASE_DIR,
        capture_output=False,
    )
    if result.returncode != 0:
        print("❌ main.py failed. Aborting.")
        sys.exit(1)

    # ── Bước 2: Khởi động Shard Nodes ─────────────────────────
    print("\n[2/4] Starting Shard Nodes...")
    for cfg in SHARD_CONFIGS:
        cmd = [
            PYTHON,
            os.path.join(BASE_DIR, "shard_node", "shard_server.py"),
            "--shard", str(cfg["shard"]),
            "--port",  str(cfg["port"]),
        ]
        p = subprocess.Popen(cmd, cwd=BASE_DIR)
        processes.append(p)
        print(f"  Shard {cfg['shard']} → PID {p.pid} (port {cfg['port']})")

    # Chờ shard nodes sẵn sàng
    print("  Waiting for shard nodes...")
    for cfg in SHARD_CONFIGS:
        ok = wait_for_port(cfg["port"])
        status = "✅ ready" if ok else "⚠  timeout"
        print(f"    Shard {cfg['shard']} port {cfg['port']}: {status}")

    # ── Bước 3: Khởi động Coordinator ─────────────────────────
    print("\n[3/4] Starting Coordinator...")
    coord_cmd = [PYTHON, os.path.join(BASE_DIR, "coordinator", "coordinator.py")]
    coord_p   = subprocess.Popen(coord_cmd, cwd=BASE_DIR)
    processes.append(coord_p)
    print(f"  Coordinator → PID {coord_p.pid} (port {COORDINATOR_PORT})")

    ok = wait_for_port(COORDINATOR_PORT)
    print(f"  Coordinator port {COORDINATOR_PORT}: {'✅ ready' if ok else '⚠  timeout'}")

    # ── Bước 4: Chạy detection qua HTTP ───────────────────────
    print("\n[4/4] Running Fraud Detection via HTTP...")
    time.sleep(3)
    try:
        with urllib.request.urlopen(
            f"http://localhost:{COORDINATOR_PORT}/detect", timeout=120
        ) as resp:
            result = json.loads(resp.read().decode())

        print("\n" + "=" * 55)
        print("  DETECTION RESULT (via HTTP)")
        print("=" * 55)
        print(f"  Fraud cycles found : {result['total_found']}")
        print(f"  Shard calls made   : {result['shard_calls']}")
        print(f"  Time elapsed       : {result['elapsed_seconds']}s")
        print(f"\n  Cycles:")
        for fc in result["fraud_cycles"]:
            print(f"    [{fc['cycle_id']}] {fc['path_str']}")
        print("=" * 55)

    except Exception as e:
        print(f"  ⚠  Detection request failed: {e}")

    # ── Giữ cluster chạy ──────────────────────────────────────
    print(f"\n  Cluster is running. Test manually:")
    print(f"    curl http://localhost:{COORDINATOR_PORT}/status")
    print(f"    curl http://localhost:{COORDINATOR_PORT}/detect")
    print(f"    curl http://localhost:5001/nodes")
    print(f"    curl http://localhost:5001/neighbors/ACC_011")
    print(f"\n  Press Ctrl+C to stop all nodes.\n")

    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        print("\n  Stopping cluster...")
        for p in processes:
            p.terminate()
        print("  All nodes stopped. Goodbye!")


if __name__ == "__main__":
    main()
