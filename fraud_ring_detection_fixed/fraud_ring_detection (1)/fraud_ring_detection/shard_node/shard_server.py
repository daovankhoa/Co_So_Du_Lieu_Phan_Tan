"""
shard_server.py
===============
HTTP Server cho mỗi Shard Node.

Chạy độc lập mỗi shard:
  python shard_node/shard_server.py --shard 0 --port 5001
  python shard_node/shard_server.py --shard 1 --port 5002
  python shard_node/shard_server.py --shard 2 --port 5003

Endpoints:
  GET /status              → trạng thái shard
  GET /nodes               → danh sách account_id trong shard
  GET /neighbors/<acc_id>  → danh sách neighbors của account
  GET /topology            → thống kê shard (node/edge count)
"""

import sys
import os
import json
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Đảm bảo import được module từ thư mục cha
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from graph.lazy_loader import ShardLazyLoader

# ──────────────────────────────────────────────────────────────
# Config (được truyền qua CLI args)
# ──────────────────────────────────────────────────────────────
SHARD_ID   = 0
PORT       = 5001
NUM_SHARDS = 3
BASE_DIR   = os.path.join(os.path.dirname(__file__), "..")
SHARD_DIR  = os.path.join(BASE_DIR, "shards")

_loader: ShardLazyLoader = None


# ──────────────────────────────────────────────────────────────
# HTTP Handler
# ──────────────────────────────────────────────────────────────

class ShardHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        # GET /status
        if self.path == "/status":
            self._json(200, {
                "shard_id": SHARD_ID,
                "port":     PORT,
                "status":   "online",
                "shard_file": os.path.join(SHARD_DIR, f"shard_{SHARD_ID}.json"),
            })

        # GET /nodes
        elif self.path == "/nodes":
            nodes = _loader.get_nodes(SHARD_ID)
            self._json(200, {
                "shard_id":  SHARD_ID,
                "nodes":     list(nodes.keys()),
                "count":     len(nodes),
            })

        # GET /neighbors/<account_id>
        elif self.path.startswith("/neighbors/"):
            account_id = self.path[len("/neighbors/"):]
            adj        = _loader.get_adjacency(SHARD_ID)
            neighbors  = adj.get(account_id, [])
            self._json(200, {
                "shard_id":   SHARD_ID,
                "account_id": account_id,
                "neighbors":  neighbors,
                "count":      len(neighbors),
            })

        # GET /topology
        elif self.path == "/topology":
            nodes = _loader.get_nodes(SHARD_ID)
            edges = _loader.get_edges(SHARD_ID)
            self._json(200, {
                "shard_id":   SHARD_ID,
                "node_count": len(nodes),
                "edge_count": len(edges),
            })

        else:
            self._json(404, {"error": f"Unknown endpoint: {self.path}"})

    def _json(self, code: int, data: dict):
        body = json.dumps(data, indent=2, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"  [Shard {SHARD_ID} HTTP] {args[0]} {args[1]}")


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────

def main():
    global SHARD_ID, PORT, _loader

    parser = argparse.ArgumentParser(description="Shard Node HTTP Server")
    parser.add_argument("--shard", type=int, required=True, help="Shard ID (0, 1, 2)")
    parser.add_argument("--port",  type=int, required=True, help="Port to listen on")
    args = parser.parse_args()

    SHARD_ID = args.shard
    PORT     = args.port

    # Khởi tạo lazy loader cho shard này
    _loader = ShardLazyLoader(shard_dir=SHARD_DIR, num_shards=NUM_SHARDS)

    # Kiểm tra shard file tồn tại
    shard_file = os.path.join(SHARD_DIR, f"shard_{SHARD_ID}.json")
    if not os.path.exists(shard_file):
        print(f"❌ Shard file not found: {shard_file}")
        print(f"   Run main.py first to generate shard files.")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"  Shard Node {SHARD_ID} running on http://localhost:{PORT}")
    print(f"  Shard file: {shard_file}")
    print(f"  Endpoints:")
    print(f"    GET /status")
    print(f"    GET /nodes")
    print(f"    GET /neighbors/<account_id>")
    print(f"    GET /topology")
    print(f"{'='*50}\n")

    server = HTTPServer(("localhost", PORT), ShardHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()