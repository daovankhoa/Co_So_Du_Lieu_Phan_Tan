"""
coordinator.py
==============
Node điều phối trung tâm (Coordinator).

Vai trò trong hệ thống phân tán:
  - Nhận yêu cầu detect fraud từ client
  - Biết shard nào đang chạy ở đâu (port nào)
  - Phân phối sub-query xuống từng shard node
  - Gộp kết quả từ các shard lại → trả về danh sách fraud cycle
  - KHÔNG giữ toàn bộ đồ thị — chỉ điều phối

Mô hình giao tiếp: HTTP/REST (localhost)
  Coordinator  →  Shard 0 (port 5001)
               →  Shard 1 (port 5002)
               →  Shard 2 (port 5003)

Chạy file này:
  python coordinator/coordinator.py
  
Sau đó gửi request:
  curl http://localhost:5000/detect
  curl http://localhost:5000/status
  curl http://localhost:5000/topology
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error
import socket

from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from collections import defaultdict

socket.setdefaulttimeout(1)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ──────────────────────────────────────────────────────────────
# Cấu hình
# ──────────────────────────────────────────────────────────────
COORDINATOR_PORT = 5000
CYCLE_LENGTH     = 4

SHARD_NODES = [
    {"shard_id": 0, "host": "localhost", "port": 5001},
    {"shard_id": 1, "host": "localhost", "port": 5002},
    {"shard_id": 2, "host": "localhost", "port": 5003},
]


# ──────────────────────────────────────────────────────────────
# HTTP helper
# ──────────────────────────────────────────────────────────────

def _get(url: str, timeout: int = 1) -> dict | None:
    """GET request đơn giản, trả về dict JSON hoặc None nếu lỗi."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [Coordinator] ⚠  Request failed {url}: {e}")
        return None


# ──────────────────────────────────────────────────────────────
# Core Coordinator Logic
# ──────────────────────────────────────────────────────────────

class FraudCoordinator:
    """
    Điều phối phát hiện fraud ring trên nhiều shard node.

    Workflow detect():
      1. Query mỗi shard → lấy danh sách node thuộc shard đó
      2. Với mỗi node, query "neighbors" từ shard chứa nó
      3. Chạy DFS 4 bước, mỗi bước có thể gọi shard khác nhau
      4. Gộp cycle tìm được, loại trùng lặp
    """

    def __init__(self):
        self.shard_nodes = SHARD_NODES
        self.found_cycles = []
        self._visited = set()

        self.neighbor_cache = {}

        self.stats = {
            "total_shard_calls": 0,
            "start_time": None,
            "elapsed_sec": None,
        }


    # ── Public ────────────────────────────────────────────────

    def check_shards_status(self) -> list[dict]:
        """Kiểm tra shard nào đang online."""
        statuses = []
        for sn in self.shard_nodes:
            url    = f"http://{sn['host']}:{sn['port']}/status"
            result = _get(url, timeout=2)
            statuses.append({
                "shard_id": sn["shard_id"],
                "port":     sn["port"],
                "online":   result is not None,
                "info":     result,
            })
        return statuses

    def detect_fraud(self) -> dict:
        """Chạy toàn bộ pipeline phát hiện fraud ring."""
        print("\n[Coordinator] Starting distributed fraud detection...")
        self.found_cycles = []
        self._visited     = set()
        self.stats["start_time"] = time.perf_counter()

        # Bước 1: Thu thập tất cả node từ mọi shard
        all_nodes = self._collect_all_nodes()
        print(f"[Coordinator] Total unique nodes: {len(all_nodes)}")

        # Bước 2: DFS từ mỗi node
        for node_id in sorted(all_nodes):
            self._dfs(path=[node_id], start=node_id, depth=CYCLE_LENGTH)

        elapsed = round(time.perf_counter() - self.stats["start_time"], 4)
        self.stats["elapsed_sec"] = elapsed

        print(f"[Coordinator] Done. Found {len(self.found_cycles)} cycles "
              f"in {elapsed}s ({self.stats['total_shard_calls']} shard calls)")

        return {
            "fraud_cycles":    self.found_cycles,
            "total_found":     len(self.found_cycles),
            "shard_calls":     self.stats["total_shard_calls"],
            "elapsed_seconds": elapsed,
        }

    def get_topology(self) -> dict:
        """Lấy thông tin topology từ tất cả shard."""
        topology = {}
        for sn in self.shard_nodes:
            url    = f"http://{sn['host']}:{sn['port']}/topology"
            result = _get(url)
            if result:
                topology[f"shard_{sn['shard_id']}"] = result
        return topology

    # ── DFS Logic ─────────────────────────────────────────────

    def _collect_all_nodes(self) -> set:
        """
        Lazy: hỏi từng shard node → lấy danh sách account_id.
        Chỉ gọi shard khi cần.
        """
        all_nodes = set()
        for sn in self.shard_nodes:
            url    = f"http://{sn['host']}:{sn['port']}/nodes"
            result = _get(url)
            self.stats["total_shard_calls"] += 1
            if result:
                all_nodes.update(result.get("nodes", []))
        return all_nodes

    def _get_neighbors(self, account_id: str) -> list[dict]:

        if account_id in self.neighbor_cache:
            return self.neighbor_cache[account_id]

        neighbors = []

        for sn in self.shard_nodes:
            url = f"http://{sn['host']}:{sn['port']}/neighbors/{account_id}"

            result = _get(url, timeout=2)

            self.stats["total_shard_calls"] += 1

            if result:
                neighbors.extend(result.get("neighbors", []))

        self.neighbor_cache[account_id] = neighbors

        return neighbors

    def _dfs(self, path: list, start: str, depth: int):
        """Distributed DFS — mỗi bước gọi shard node qua HTTP."""
        if depth == 0:
            return
        current   = path[-1]
        neighbors = self._get_neighbors(current)

        for nb in neighbors:
            next_node = nb["to"]
            if depth == 1:
                if next_node == start:
                    self._register_cycle(path + [start])
            else:
                if next_node not in path:
                    self._dfs(path + [next_node], start, depth - 1)

    def _register_cycle(self, cycle: list):
        nodes = cycle[:-1]
        if len(nodes) != CYCLE_LENGTH:
            return
        canon = tuple(min(
            [nodes[i:] + nodes[:i] for i in range(len(nodes))]
        ))
        if canon in self._visited:
            return
        self._visited.add(canon)
        entry = {
            "cycle_id": f"FRAUD_{len(self.found_cycles):02d}",
            "accounts": nodes,
            "path_str": " -> ".join(cycle),
        }
        self.found_cycles.append(entry)
        print(f"  [Coordinator] 🚨 FRAUD: {entry['path_str']}")


# ──────────────────────────────────────────────────────────────
# HTTP Server
# ──────────────────────────────────────────────────────────────

_coordinator = FraudCoordinator()


class CoordinatorHandler(BaseHTTPRequestHandler):
    """HTTP handler cho Coordinator node."""

    def do_GET(self):
        if self.path == "/detect":
            result = _coordinator.detect_fraud()
            self._json(200, result)

        elif self.path == "/status":
            shards = _coordinator.check_shards_status()
            self._json(200, {
                "coordinator": "online",
                "port": COORDINATOR_PORT,
                "shards": shards,
            })

        elif self.path == "/topology":
            topo = _coordinator.get_topology()
            self._json(200, topo)

        else:
            self._json(404, {"error": "Unknown endpoint"})

    def _json(self, code: int, data: dict):
        body = json.dumps(data, indent=2, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError):
            pass

    def log_message(self, fmt, *args):
        # Giữ log gọn hơn
        print(f"  [Coordinator HTTP] {args[0]} {args[1]}")


def run_server():
    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

    server = ThreadedHTTPServer(("localhost", COORDINATOR_PORT), CoordinatorHandler)
    print(f"\n{'='*55}")
    print(f"  Coordinator running on http://localhost:{COORDINATOR_PORT}")
    print(f"  Endpoints:")
    print(f"    GET /detect    → Run fraud detection")
    print(f"    GET /status    → Check shard status")
    print(f"    GET /topology  → Topology info")
    print(f"{'='*55}\n")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
