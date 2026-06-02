"""
relational_store.py
===================
Multi-Model Layer 1: Relational (SQLite)

Lưu thông tin tài khoản dạng bảng quan hệ.
Tách biệt hoàn toàn với Graph layer — đây là điểm mấu chốt
để chứng minh Multi-Model Integration.

Schema:
    accounts(account_id PK, owner, balance, risk_score, account_type, country)
    transactions(tx_id PK, from_acc, to_acc, amount, is_fraud_edge, ring_id)
"""

import sqlite3
import os
import random

random.seed(42)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "accounts.db")

ACCOUNT_TYPES = ["personal", "business", "offshore", "shell"]
COUNTRIES     = ["VN", "SG", "CN", "US", "KY", "BVI"]  # KY/BVI = tax havens


class RelationalStore:
    """
    SQLite store cho dữ liệu tài khoản và giao dịch.

    Đây là 'Relational fragment' trong kiến trúc Multi-Model:
      - Graph  fragment → ShardLazyLoader  (adjacency list)
      - Relational fragment → RelationalStore (SQLite)
      - Document fragment  → DocumentStore  (JSON documents)
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn    = None

    # ──────────────────────────────────────────────────
    # Setup
    # ──────────────────────────────────────────────────

    def connect(self):
        """Mở kết nối SQLite."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row   # Trả dict thay vì tuple
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_id   TEXT PRIMARY KEY,
                owner        TEXT NOT NULL,
                balance      REAL NOT NULL,
                risk_score   REAL NOT NULL,
                account_type TEXT NOT NULL,
                country      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                tx_id         TEXT PRIMARY KEY,
                from_acc      TEXT NOT NULL,
                to_acc        TEXT NOT NULL,
                amount        REAL NOT NULL,
                is_fraud_edge INTEGER NOT NULL DEFAULT 0,
                ring_id       TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_tx_from ON transactions(from_acc);
            CREATE INDEX IF NOT EXISTS idx_tx_to   ON transactions(to_acc);
            CREATE INDEX IF NOT EXISTS idx_risk     ON accounts(risk_score);
        """)
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()

    # ──────────────────────────────────────────────────
    # Load từ dataset
    # ──────────────────────────────────────────────────

    def load_from_dataset(self, dataset: dict):
        """
        Nạp accounts + transactions từ dataset vào SQLite.
        Thêm các trường relational (account_type, country) không có trong Graph.
        """
        # Accounts
        account_rows = []
        for acc in dataset["accounts"]:
            account_rows.append((
                acc["account_id"],
                acc["owner"],
                acc["balance"],
                acc["risk_score"],
                random.choice(ACCOUNT_TYPES),   # Thêm trường mới
                random.choice(COUNTRIES),        # Thêm trường mới
            ))

        self.conn.executemany(
            "INSERT OR REPLACE INTO accounts VALUES (?,?,?,?,?,?)",
            account_rows
        )

        # Transactions
        tx_rows = []
        for tx in dataset["transactions"]:
            tx_rows.append((
                tx["tx_id"],
                tx["from"],
                tx["to"],
                tx["amount"],
                1 if tx.get("is_fraud_edge") else 0,
                tx.get("ring_id"),
            ))

        self.conn.executemany(
            "INSERT OR REPLACE INTO transactions VALUES (?,?,?,?,?,?)",
            tx_rows
        )

        self.conn.commit()
        print(f"  [RelationalStore] Loaded {len(account_rows)} accounts, "
              f"{len(tx_rows)} transactions into SQLite")

    # ──────────────────────────────────────────────────
    # Query
    # ──────────────────────────────────────────────────

    def get_account(self, account_id: str) -> dict | None:
        """Lấy thông tin một tài khoản."""
        row = self.conn.execute(
            "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_accounts_batch(self, account_ids: list) -> dict:
        """Lấy nhiều tài khoản cùng lúc — tối ưu cho cycle enrichment."""
        placeholders = ",".join("?" * len(account_ids))
        rows = self.conn.execute(
            f"SELECT * FROM accounts WHERE account_id IN ({placeholders})",
            account_ids
        ).fetchall()
        return {row["account_id"]: dict(row) for row in rows}

    def get_transactions_in_cycle(self, account_ids: list) -> list:
        """
        Lấy tất cả giao dịch GIỮA các tài khoản trong một cycle.
        Graph biết 'ai nối với ai', Relational biết 'số tiền, thời gian'.
        """
        placeholders = ",".join("?" * len(account_ids))
        rows = self.conn.execute(
            f"""
            SELECT * FROM transactions
            WHERE from_acc IN ({placeholders})
              AND to_acc   IN ({placeholders})
            """,
            account_ids + account_ids
        ).fetchall()
        return [dict(r) for r in rows]

    def get_high_risk_accounts(self, threshold: float = 0.7) -> list:
        """Lấy các tài khoản có risk_score cao — dùng cho phân tích bổ sung."""
        rows = self.conn.execute(
            "SELECT * FROM accounts WHERE risk_score >= ? ORDER BY risk_score DESC",
            (threshold,)
        ).fetchall()
        return [dict(r) for r in rows]
