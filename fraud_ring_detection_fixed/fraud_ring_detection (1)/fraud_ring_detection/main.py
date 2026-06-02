"""
main.py
=======
Entry point — Chạy toàn bộ pipeline Fraud Ring Detection.

Luồng chạy:
  1. Sinh dữ liệu giả lập (accounts + transactions + injected fraud rings)
  2. Partition đồ thị thành 3 shard (Vertex-Cut)
  3. Khởi tạo LazyLoader (chưa tải gì cả)
  4. Chạy Distributed Fraud Detector (DFS xuyên shard, lazy loading)
  5. Phân tích Topology (Edge-Cut, Density, Load Balance)
  6. In báo cáo Lazy Loading (chứng minh không tải toàn bộ graph)
  7. Multi-Model Integration (Graph + Relational + Document JOIN)
  8. So sánh kết quả với ground truth
"""

import sys
import os
import json

# Đảm bảo import đúng module từ thư mục gốc
sys.path.insert(0, os.path.dirname(__file__))

from data.generate_data              import main as generate_data
from graph.partitioner               import partition
from graph.lazy_loader               import ShardLazyLoader
from detection.fraud_detector        import DistributedFraudDetector
from analysis.topology_analyzer      import TopologyAnalyzer
from multimodel.relational_store     import RelationalStore
from multimodel.document_store       import DocumentStore
from multimodel.integrator           import MultiModelIntegrator


# ─────────────────────────────────────────────
# Cấu hình
# ─────────────────────────────────────────────
BASE_DIR   = os.path.dirname(__file__)
SHARD_DIR  = os.path.join(BASE_DIR, "shards")
NUM_SHARDS = 3


def verify_results(found_cycles: list, ground_truth: list):
    """
    So sánh kết quả phát hiện với ground truth được nhúng vào dataset.
    """
    print("\n" + "=" * 60)
    print("  VERIFICATION vs GROUND TRUTH")
    print("=" * 60)

    gt_sets = [frozenset(ring["members"]) for ring in ground_truth]
    found_sets = [frozenset(fc["accounts"]) for fc in found_cycles]

    true_positives  = 0
    false_positives = 0

    for fs in found_sets:
        if fs in gt_sets:
            true_positives += 1
        else:
            false_positives += 1

    false_negatives = len(gt_sets) - true_positives

    print(f"  Ground Truth rings  : {len(gt_sets)}")
    print(f"  Detected rings      : {len(found_sets)}")
    print(f"  True Positives      : {true_positives}")
    print(f"  False Positives     : {false_positives}")
    print(f"  False Negatives     : {false_negatives}")

    precision = true_positives / len(found_sets) if found_sets else 0
    recall    = true_positives / len(gt_sets)    if gt_sets    else 0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0)

    print(f"\n  Precision : {precision:.2%}")
    print(f"  Recall    : {recall:.2%}")
    print(f"  F1 Score  : {f1:.2%}")

    if false_negatives > 0:
        print(f"\n  ⚠  Missed rings (might be due to data sparsity):")
        for ring in ground_truth:
            if frozenset(ring["members"]) not in found_sets:
                print(f"     {ring['ring_id']}: {' -> '.join(ring['members'])}")

    print("=" * 60)


def save_results(found_cycles: list, topo_report: dict, enriched: list = None):
    """Lưu kết quả ra file JSON để nộp bài."""
    result = {
        "fraud_cycles_detected": found_cycles,
        "topology_analysis":     topo_report,
        "multimodel_reports":    enriched or [],
    }
    out_path = os.path.join(BASE_DIR, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved → {out_path}")


def main():
    print("\n" + "█" * 60)
    print("  PROJECT #136: Distributed Graph Pattern Matching")
    print("              Fraud Ring Detection System")
    print("█" * 60)

    # ── STEP 1: Sinh dữ liệu ──────────────────────────────────
    print("\n[STEP 1] Generating dataset...")
    dataset = generate_data()
    ground_truth = dataset["ground_truth"]

    # ── STEP 2: Partition đồ thị ──────────────────────────────
    print("\n[STEP 2] Partitioning graph (Vertex-Cut)...")
    shard_meta = partition(dataset, num_shards=NUM_SHARDS, output_dir=SHARD_DIR)

    # ── STEP 3: Khởi tạo LazyLoader ───────────────────────────
    print("\n[STEP 3] Initializing Lazy Loader (no data loaded yet)...")
    loader = ShardLazyLoader(shard_dir=SHARD_DIR, num_shards=NUM_SHARDS)

    # ── STEP 4: Phát hiện Fraud Ring ──────────────────────────
    print("\n[STEP 4] Running Distributed Fraud Detection...")
    detector     = DistributedFraudDetector(loader=loader)
    found_cycles = detector.detect()

    # ── STEP 5: Phân tích Topology ────────────────────────────
    print("\n[STEP 5] Running Topology Analysis...")
    analyzer    = TopologyAnalyzer(loader=loader, shard_meta=shard_meta)
    topo_report = analyzer.analyze()

    # ── STEP 6: Báo cáo Lazy Loading ──────────────────────────
    print("\n[STEP 6] Lazy Loading Report...")
    loader.print_load_report()

    # ── STEP 7: Multi-Model Integration ───────────────────────
    print("\n[STEP 7] Multi-Model Integration (Graph + Relational + Document)...")

    # Layer 1: Relational — nạp accounts vào SQLite
    rel_store = RelationalStore()
    rel_store.connect()
    rel_store.load_from_dataset(dataset)

    # Layer 2: Document — khởi tạo JSON document store
    doc_store = DocumentStore()

    # JOIN: Graph cycles → enrich với Relational → lưu Document
    integrator    = MultiModelIntegrator(relational=rel_store, document=doc_store)
    enriched      = integrator.enrich_cycles(found_cycles)

    # In document reports
    doc_store.print_summary()

    # Cross-model analytics
    integrator.cross_model_analysis()

    rel_store.close()

    # ── STEP 8: Verification ──────────────────────────────────
    print("\n[STEP 8] Verifying results...")
    verify_results(found_cycles, ground_truth)

    # ── Lưu kết quả ───────────────────────────────────────────
    save_results(found_cycles, topo_report, enriched)

    print("\n" + "█" * 60)
    print("  Pipeline complete!")
    print("█" * 60 + "\n")


if __name__ == "__main__":
    main()
