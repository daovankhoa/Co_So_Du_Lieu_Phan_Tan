"""
lazy_loader.py
==============
LAZY LOADING cho dữ liệu shard.

Nguyên tắc Lazy Loading trong CSDL phân tán:
  - Không tải toàn bộ shard vào RAM ngay từ đầu.
  - Chỉ đọc file shard khi có request truy vấn đến shard đó.
  - Cache shard đã tải để tránh đọc file lặp lại.
  - Ghi log để thấy "khi nào" dữ liệu thực sự được tải.

Đây là điểm quan trọng để chứng minh hệ thống KHÔNG kéo toàn bộ
đồ thị về một node (theo yêu cầu đề bài).
"""

import json
import os
import time
from typing import Optional


class ShardLazyLoader:
    """
    Quản lý lazy loading tất cả các shard.

    Attributes:
        shard_dir (str): Thư mục chứa file shard JSON
        _cache (dict):   Cache các shard đã được tải
        _load_log (list): Lịch sử các lần tải dữ liệu
    """

    def __init__(self, shard_dir: str, num_shards: int):
        self.shard_dir  = shard_dir
        self.num_shards = num_shards
        self._cache     = {}        # { shard_id: shard_data }
        self._load_log  = []        # Để báo cáo cuối cùng
        print(f"[LazyLoader] Initialized. {num_shards} shards at '{shard_dir}'")
        print(f"[LazyLoader] ⚡ No data loaded yet — truly lazy!")

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def get_adjacency(self, shard_id: int) -> dict:
        """Lấy adjacency list của shard (lazy)."""
        shard = self._load_shard(shard_id)
        return shard.get("adjacency", {})

    def get_neighbors(self, account_id: str, shard_id: int) -> list:
        """Lấy danh sách hàng xóm của account_id trong shard_id."""
        adj = self.get_adjacency(shard_id)
        return adj.get(account_id, [])

    def get_nodes(self, shard_id: int) -> dict:
        """Lấy tất cả node trong shard."""
        shard = self._load_shard(shard_id)
        return shard.get("nodes", {})

    def get_edges(self, shard_id: int) -> list:
        """Lấy tất cả edge trong shard."""
        shard = self._load_shard(shard_id)
        return shard.get("edges", [])

    def find_shards_for_account(self, account_id: str) -> list[int]:
        """
        Tìm tất cả shard chứa account_id.
        Dùng khi cần traverse cross-shard.
        Lazy: chỉ load shard nào chưa được cache khi cần kiểm tra.
        """
        result = []
        for shard_id in range(self.num_shards):
            nodes = self.get_nodes(shard_id)
            if account_id in nodes:
                result.append(shard_id)
        return result

    def get_neighbors_all_shards(self, account_id: str) -> list[dict]:
        """
        Lấy TẤT CẢ hàng xóm của account_id từ mọi shard chứa nó.
        Đây là bước cross-shard traversal.
        """
        neighbors = []
        shards = self.find_shards_for_account(account_id)
        for shard_id in shards:
            nbrs = self.get_neighbors(account_id, shard_id)
            for n in nbrs:
                n["_from_shard"] = shard_id   # Tag nguồn để debug
            neighbors.extend(nbrs)
        return neighbors

    # ──────────────────────────────────────────
    # Reporting
    # ──────────────────────────────────────────

    def print_load_report(self):
        """In báo cáo các shard đã được tải (để chứng minh lazy loading)."""
        print("\n" + "═" * 55)
        print("  LAZY LOADING REPORT")
        print("═" * 55)
        loaded_ids = list(self._cache.keys())
        print(f"  Shards loaded into memory: {sorted(loaded_ids)} / {list(range(self.num_shards))}")
        print(f"  Total load events        : {len(self._load_log)}")
        for entry in self._load_log:
            print(f"    [{entry['timestamp']}] Shard {entry['shard_id']} loaded "
                  f"({entry['load_time_ms']} ms) — triggered by: {entry['trigger']}")
        unloaded = [i for i in range(self.num_shards) if i not in loaded_ids]
        if unloaded:
            print(f"\n  ✅ Shards NOT loaded (still on disk): {unloaded}")
            print("     → Proves system avoids pulling entire graph to one node!")
        print("═" * 55)

    # ──────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────

    def _load_shard(self, shard_id: int) -> dict:
        """
        Core lazy load logic:
        - Nếu shard đã cache → trả về ngay (O(1))
        - Nếu chưa → đọc từ disk, cache lại
        """
        if shard_id in self._cache:
            return self._cache[shard_id]   # Cache hit — không đọc file

        # Cache miss → đọc file
        shard_file = os.path.join(self.shard_dir, f"shard_{shard_id}.json")
        if not os.path.exists(shard_file):
            raise FileNotFoundError(f"Shard file not found: {shard_file}")

        import traceback
        trigger = traceback.extract_stack()[-3].name  # Hàm gọi load

        t0 = time.perf_counter()
        with open(shard_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        self._cache[shard_id] = data

        log_entry = {
            "shard_id":     shard_id,
            "timestamp":    time.strftime("%H:%M:%S"),
            "load_time_ms": elapsed_ms,
            "trigger":      trigger,
        }
        self._load_log.append(log_entry)
        print(f"  [LazyLoader] 🔄 Shard {shard_id} loaded from disk "
              f"({elapsed_ms} ms) — triggered by '{trigger}'")

        return data
