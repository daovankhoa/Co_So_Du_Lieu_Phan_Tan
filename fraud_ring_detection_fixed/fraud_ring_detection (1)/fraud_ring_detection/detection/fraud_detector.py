"""
fraud_detector.py
=================
Thuật toán phát hiện Fraud Ring (vòng gian lận) trên đồ thị phân tán.

Pattern cần tìm: Cycle gồm 4 đỉnh (tài khoản)
  A -> B -> C -> D -> A  (4 account chuyển tiền vòng tròn)

Thuật toán: Distributed DFS (Depth-First Search)
  - Bắt đầu từ mỗi node khởi điểm (start_node)
  - Dùng LazyLoader để lấy neighbors từ shard phù hợp
  - Chỉ load shard khi cần (lazy)
  - Nếu sau 3 bước đi lại về start_node → tìm thấy cycle độ dài 4
  - Canonical form để tránh đếm trùng cùng một cycle

Đây là phần chứng minh "distributed query" theo yêu cầu đề bài.
"""

import time
from graph.lazy_loader import ShardLazyLoader


CYCLE_LENGTH     = 4
FRAUD_MIN_AMOUNT = 5_000


class DistributedFraudDetector:
    """
    Phát hiện fraud ring trên đồ thị phân tán.

    Attributes:
        loader (ShardLazyLoader): Lazy loader để truy cập shard
        found_cycles (list):      Các cycle đã tìm thấy
        _visited_cycles (set):    Tập canonical form để tránh trùng
        stats (dict):             Thống kê quá trình tìm kiếm
    """

    def __init__(self, loader: ShardLazyLoader):
        self.loader          = loader
        self.found_cycles    = []
        self._visited_cycles = set()
        self.stats = {
            "nodes_visited":    0,
            "shards_accessed":  set(),
            "dfs_calls":        0,
            "start_time":       None,
            "end_time":         None,
        }

    # ──────────────────────────────────────────────────
    # Public
    # ──────────────────────────────────────────────────

    def detect(self) -> list[dict]:
        """
        Chạy thuật toán phát hiện fraud ring trên toàn đồ thị phân tán.

        Workflow:
          1. Thu thập tất cả node từ tất cả shard (lazy)
          2. Với mỗi node, chạy DFS sâu 3 bước
          3. Nếu bước thứ 3 quay về start → fraud cycle!
        """
        print("\n" + "=" * 60)
        print("  DISTRIBUTED FRAUD RING DETECTION")
        print(f"  Target Pattern: Cycle of {CYCLE_LENGTH} accounts")
        print("=" * 60)

        self.stats["start_time"] = time.perf_counter()

        # Bước 1: Lấy tất cả node từ mọi shard (lazy loading)
        all_nodes = self._collect_all_nodes()
        print(f"\n  Total unique accounts found: {len(all_nodes)}")

        # Bước 2: DFS từ mỗi node
        for node_id in sorted(all_nodes):
            self._dfs(
                path=[node_id],
                start=node_id,
                depth=CYCLE_LENGTH,  # Cần đi thêm 4 bước để tạo cycle 4 đỉnh
            )

        self.stats["end_time"] = time.perf_counter()
        self.stats["shards_accessed"] = list(self.stats["shards_accessed"])

        self._print_results()
        return self.found_cycles

    # ──────────────────────────────────────────────────
    # Core Algorithm
    # ──────────────────────────────────────────────────

    def _dfs(self, path: list, start: str, depth: int):
        """
        Distributed DFS — đệ quy tìm cycle.

        Args:
            path:  Đường đi hiện tại [node_0, node_1, ...]
            start: Node khởi đầu (cần quay về để tạo cycle)
            depth: Số bước còn lại được phép đi
        """
        self.stats["dfs_calls"] += 1
        current = path[-1]

        # Lấy neighbors từ tất cả shard (cross-shard traversal, lazy)
        neighbors = self.loader.get_neighbors_all_shards(current)
        self.stats["nodes_visited"] += 1

        # Ghi nhận shard nào được truy cập
        for n in neighbors:
            if "_from_shard" in n:
                self.stats["shards_accessed"].add(n["_from_shard"])

        for neighbor_info in neighbors:
            next_node = neighbor_info["to"]
            amt = neighbor_info.get("amount", 0)
            is_fraud = neighbor_info.get("is_fraud_edge", False)

            if amt < FRAUD_MIN_AMOUNT and not is_fraud:
                continue

            if depth == 1:
                # Bước cuối cùng: phải quay về start để tạo cycle
                if next_node == start:
                    cycle = path + [start]
                    self._register_cycle(cycle, neighbor_info)
            else:
                # Chưa đến bước cuối: tiếp tục đi sâu hơn
                # Không đi vào node đã thăm (tránh vòng lặp không hợp lệ)
                # Nhưng cho phép quay về start ở bước cuối
                if next_node not in path:
                    self._dfs(
                        path=path + [next_node],
                        start=start,
                        depth=depth - 1,
                    )

    def _register_cycle(self, cycle: list, last_edge: dict):
        """Đăng ký một cycle mới (tránh trùng bằng canonical form)."""
        # Canonical form: sorted rotation nhỏ nhất
        nodes = cycle[:-1]   # Bỏ phần tử cuối (= start, bị lặp)
        # Chỉ chấp nhận cycle đúng độ dài CYCLE_LENGTH
        if len(nodes) != CYCLE_LENGTH:
            return
        canon   = self._canonical(nodes)

        if canon in self._visited_cycles:
            return   # Đã tìm thấy cycle này rồi

        self._visited_cycles.add(canon)
        self.found_cycles.append({
            "cycle_id":   f"FRAUD_{len(self.found_cycles):02d}",
            "accounts":   nodes,
            "path_str":   " -> ".join(cycle),
            "length":     len(nodes),
        })
        print(f"\n  🚨 FRAUD CYCLE FOUND: {' -> '.join(cycle)}")

    # ──────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────

    def _collect_all_nodes(self) -> set:
        """Thu thập tất cả node từ mọi shard (mỗi shard lazy-loaded)."""
        all_nodes = set()
        for shard_id in range(self.loader.num_shards):
            nodes = self.loader.get_nodes(shard_id)   # Lazy load ở đây
            all_nodes.update(nodes.keys())
        return all_nodes

    def _canonical(self, nodes: list) -> tuple:
        """
        Tạo canonical form của một cycle để tránh đếm trùng.
        Ví dụ: [A,B,C,D], [B,C,D,A], [C,D,A,B] đều → cùng canonical.
        """
        rotations = [nodes[i:] + nodes[:i] for i in range(len(nodes))]
        return tuple(min(rotations))

    def _print_results(self):
        elapsed = self.stats["end_time"] - self.stats["start_time"]
        print("\n" + "=" * 60)
        print("  DETECTION RESULTS")
        print("=" * 60)
        print(f"  Fraud cycles found    : {len(self.found_cycles)}")
        print(f"  Execution time        : {elapsed:.4f} seconds")
        print(f"  DFS calls             : {self.stats['dfs_calls']}")
        print(f"  Nodes visited         : {self.stats['nodes_visited']}")
        print(f"  Shards accessed       : {sorted(self.stats['shards_accessed'])}")
        print(f"\n  Detected Fraud Rings:")
        for fc in self.found_cycles:
            print(f"    [{fc['cycle_id']}] {fc['path_str']}")
        print("=" * 60)
