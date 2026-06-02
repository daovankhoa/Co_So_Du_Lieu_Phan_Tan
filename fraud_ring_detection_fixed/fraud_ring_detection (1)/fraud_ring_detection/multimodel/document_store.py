"""
document_store.py
=================
Multi-Model Layer 2: Document Store (JSON)

Lưu báo cáo fraud dạng document — mỗi cycle là một document
với cấu trúc lồng nhau tự do (không cần schema cố định như SQL).

Đây là 'Document fragment' trong kiến trúc Multi-Model:
  - Graph      fragment → ShardLazyLoader   (adjacency list)
  - Relational fragment → RelationalStore   (SQLite)
  - Document   fragment → DocumentStore     (JSON documents)
"""

import json
import os
from datetime import datetime


STORE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fraud_reports.json")


class DocumentStore:
    """
    JSON Document Store cho fraud reports.

    Mỗi document là một fraud cycle report đầy đủ:
    {
        "cycle_id": "FRAUD_00",
        "detected_at": "2024-...",
        "graph_data": { path, length, shards_crossed },   ← từ Graph layer
        "relational_data": { accounts[], transactions[] }, ← từ SQL layer
        "risk_assessment": { total_amount, avg_risk, ... } ← computed
    }
    """

    def __init__(self, store_path: str = STORE_PATH):
        self.store_path = store_path
        self.documents  = {}

    # ──────────────────────────────────────────────────
    # Core
    # ──────────────────────────────────────────────────

    def save_report(self, cycle_id: str, document: dict):
        """Lưu một fraud report document."""
        document["saved_at"] = datetime.now().isoformat()
        self.documents[cycle_id] = document

    def get_report(self, cycle_id: str) -> dict | None:
        return self.documents.get(cycle_id)

    def get_all_reports(self) -> list:
        return list(self.documents.values())

    def flush_to_disk(self):
        """Ghi tất cả documents ra file JSON."""
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, indent=2, ensure_ascii=False)
        print(f"  [DocumentStore] {len(self.documents)} reports → {self.store_path}")

    # ──────────────────────────────────────────────────
    # Query
    # ──────────────────────────────────────────────────

    def query_high_risk(self, min_avg_risk: float = 0.6) -> list:
        """Tìm các cycle có avg_risk_score cao."""
        return [
            doc for doc in self.documents.values()
            if doc.get("risk_assessment", {}).get("avg_risk_score", 0) >= min_avg_risk
        ]

    def query_high_amount(self, min_amount: float = 50000) -> list:
        """Tìm các cycle có tổng tiền giao dịch lớn."""
        return [
            doc for doc in self.documents.values()
            if doc.get("risk_assessment", {}).get("total_transaction_amount", 0) >= min_amount
        ]

    def print_summary(self):
        """In tóm tắt tất cả fraud reports."""
        print("\n" + "=" * 60)
        print("  MULTI-MODEL FRAUD REPORTS (Document Store)")
        print("=" * 60)

        for doc in self.documents.values():
            ra  = doc.get("risk_assessment", {})
            rd  = doc.get("relational_data", {})
            gd  = doc.get("graph_data", {})
            accs = rd.get("accounts", [])

            print(f"\n  [{doc['cycle_id']}] {gd.get('path_str', '')}")
            print(f"    Total amount  : ${ra.get('total_transaction_amount', 0):,.0f}")
            print(f"    Avg risk score: {ra.get('avg_risk_score', 0):.3f}  "
                  f"{'⚠ HIGH RISK' if ra.get('avg_risk_score', 0) >= 0.6 else ''}")

            countries = [a.get("country", "?") for a in accs]
            types     = [a.get("account_type", "?") for a in accs]
            print(f"    Countries     : {', '.join(countries)}")
            print(f"    Account types : {', '.join(types)}")

            offshore = [a["account_id"] for a in accs
                        if a.get("country") in ("KY", "BVI") or
                           a.get("account_type") in ("offshore", "shell")]
            if offshore:
                print(f"    ⚠ Offshore/Shell accounts: {', '.join(offshore)}")

        print("=" * 60)
