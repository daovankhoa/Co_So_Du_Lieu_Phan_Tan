# Fraud Ring Detection — Distributed Graph Pattern Matching

> **Project #136 — Category 14: Distributed Graph Database**  
> Môn: Cơ sở Dữ liệu Phân tán — Trường ĐH BCVT TP.HCM

---

## Mô tả

Hệ thống phát hiện **fraud ring** (vòng gian lận tài chính) trên đồ thị giao dịch phân tán.  
Tìm chu trình 4 đỉnh dạng `A → B → C → D → A` xuyên nhiều shard mà **không kéo toàn bộ đồ thị về một node**.

**Kiến trúc Multi-Model:**
- **Graph** — Vertex-Cut Partitioning, Distributed DFS, Lazy Loading
- **Relational** — SQLite lưu thông tin tài khoản
- **Document** — JSON Store lưu fraud reports đầy đủ

---

## Yêu cầu thư viện

### Không cần cài thêm gì — chỉ dùng Python Standard Library

| Thư viện | Loại | Dùng trong |
|---|---|---|
| `sqlite3` | Built-in | Relational store (accounts.db) |
| `json` | Built-in | Đọc/ghi shard files, document store |
| `http.server` | Built-in | Shard Node HTTP server |
| `urllib.request` | Built-in | HTTP calls giữa Coordinator và Shard |
| `socketserver` | Built-in | Threaded HTTP server cho Coordinator |
| `hashlib` | Built-in | MD5 hash để Vertex-Cut partition |
| `argparse` | Built-in | CLI args cho shard_server.py |
| `subprocess` | Built-in | Khởi động các process trong run_cluster.py |
| `collections` | Built-in | `defaultdict` trong topology analyzer |
| `math`, `random`, `os`, `sys`, `time`, `threading` | Built-in | Tiện ích chung |

### Yêu cầu duy nhất

```
Python >= 3.10
```

> Dùng type hint `dict | None` (union type mới từ Python 3.10).  
> Kiểm tra version: `python --version`

### Tùy chọn (cho benchmark chart)

```bash
pip install matplotlib
```

Chỉ cần nếu muốn xuất biểu đồ `benchmark_chart.png` khi chạy `benchmark.py`.  
Nếu không cài, benchmark vẫn chạy bình thường và in bảng số liệu ra terminal.

---

## Cấu trúc thư mục

```
fraud_ring_detection/
│
├── main.py                          # ← CHẠY FILE NÀY (pipeline đầy đủ 8 bước)
├── run_cluster.py                   # Khởi động cluster HTTP (4 node)
├── benchmark.py                     # So sánh local vs coordinator
├── requirements.txt
│
├── data/
│   ├── generate_data.py             # Sinh 50 tài khoản, 136 giao dịch, 4 fraud rings
│   ├── transactions_raw.json        # ← tự tạo khi chạy
│   ├── accounts.db                  # ← tự tạo khi chạy (SQLite)
│   └── fraud_reports.json           # ← tự tạo khi chạy (Document store)
│
├── graph/
│   ├── partitioner.py               # Vertex-Cut: chia đồ thị → 3 shard JSON
│   └── lazy_loader.py               # Lazy loading: chỉ đọc shard khi DFS cần
│
├── detection/
│   └── fraud_detector.py            # Distributed DFS: tìm chu trình 4 đỉnh
│
├── analysis/
│   └── topology_analyzer.py         # Edge-Cut ratio, Gini, Cluster Density
│
├── multimodel/                      # Multi-Model Integration
│   ├── relational_store.py          # Layer 1: SQLite
│   ├── document_store.py            # Layer 2: JSON Document
│   └── integrator.py                # JOIN Graph + Relational + Document
│
├── coordinator/
│   └── coordinator.py               # HTTP Coordinator (port 5000)
│
├── shard_node/
│   └── shard_server.py              # HTTP Shard server (port 5001–5003)
│
├── shards/                          # ← tự tạo khi chạy
│   ├── shard_0.json
│   ├── shard_1.json
│   └── shard_2.json
│
└── results.json                     # ← output cuối cùng
```

---

## Cách chạy

### Cách 1 — Pipeline offline (đơn giản nhất)

```bash
cd "fraud_ring_detection (1)/fraud_ring_detection"
python main.py
```

Chạy đủ **8 bước** tự động:

```
[STEP 1] Generating dataset...
[STEP 2] Partitioning graph (Vertex-Cut)...
[STEP 3] Initializing Lazy Loader...
[STEP 4] Running Distributed Fraud Detection...
[STEP 5] Running Topology Analysis...
[STEP 6] Lazy Loading Report...
[STEP 7] Multi-Model Integration (Graph + Relational + Document)...
[STEP 8] Verifying results...
```

---

### Cách 2 — Cluster HTTP (mô phỏng hệ thống phân tán thật)

Chạy 1 lệnh duy nhất, tự động khởi động 4 node:

```bash
python run_cluster.py
```

Hoặc thủ công mở **4 terminal riêng biệt**:

```bash
# Terminal 1 — Shard Node 0
python shard_node/shard_server.py --shard 0 --port 5001

# Terminal 2 — Shard Node 1
python shard_node/shard_server.py --shard 1 --port 5002

# Terminal 3 — Shard Node 2
python shard_node/shard_server.py --shard 2 --port 5003

# Terminal 4 — Coordinator
python coordinator/coordinator.py
```

Sau đó gọi API:

```bash
curl http://localhost:5000/detect    # Chạy fraud detection
curl http://localhost:5000/status    # Kiểm tra trạng thái các shard
curl http://localhost:5000/topology  # Thông tin topology
curl http://localhost:5001/nodes     # Danh sách node trong shard 0
```

> **Lưu ý:** Phải chạy `python main.py` ít nhất 1 lần trước để tạo shard files.

---

### Cách 3 — Benchmark so sánh Local vs Coordinator

```bash
python benchmark.py
```

So sánh thời gian chạy giữa:
- **main.py** (đọc file local, không có network overhead)
- **Coordinator** (HTTP calls, bị ảnh hưởng bởi network latency)

Output: bảng số liệu + `benchmark_results.json` + `benchmark_chart.png` (nếu có matplotlib).

---

## Kết quả mẫu

```
Ground Truth rings  : 4
Detected rings      : 8
True Positives      : 4      ← Tìm đúng cả 4 fraud rings
False Positives     : 4      ← Cycle ngẫu nhiên trong dataset nhỏ
False Negatives     : 0      ← Không bỏ sót ring nào

Precision : 50.00%
Recall    : 100.00%          ← Chỉ số quan trọng nhất
F1 Score  : 66.67%

Edge-Cut Ratio      : 74.26%
Gini Coefficient    : 0.093  (load balance tốt)
Node Overlap        : 94%
Execution time      : ~13ms
```

---

## File output sau khi chạy

| File | Mô tả |
|---|---|
| `shards/shard_0.json` | Dữ liệu shard 0 (45 edges) |
| `shards/shard_1.json` | Dữ liệu shard 1 (55 edges) |
| `shards/shard_2.json` | Dữ liệu shard 2 (36 edges) |
| `data/accounts.db` | SQLite database — thông tin tài khoản |
| `data/fraud_reports.json` | Document store — fraud reports đầy đủ |
| `results.json` | Kết quả tổng hợp để nộp bài |

---

## Kiến trúc CAP

Hệ thống theo mô hình **AP (Availability + Partition Tolerance)**:
- **Partition**: đồ thị chia thành 3 shard độc lập
- **Availability**: Lazy Loader luôn trả kết quả, không block chờ đồng bộ
- **Consistency**: hi sinh — không có lock hay quorum write

---

*Đề tài #136 — Distributed Graph Pattern Matching | Fraud Ring Detection*
