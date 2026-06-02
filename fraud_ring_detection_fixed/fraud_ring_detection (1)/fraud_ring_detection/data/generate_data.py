"""
generate_data.py
================
Tạo dataset giả lập: Financial_Transactions
- Accounts (Nodes): Tài khoản ngân hàng
- Transfers (Edges): Giao dịch chuyển tiền
- Cố tình nhúng các vòng gian lận (fraud cycles) để test
"""

import json
import random
import os

random.seed(42)

# ──────────────────────────────────────────────
# Tham số
# ──────────────────────────────────────────────
NUM_ACCOUNTS   = 50    # Tổng số tài khoản
NUM_NORMAL_TX  = 120   # Giao dịch bình thường
NUM_FRAUD_RINGS = 4    # Số vòng gian lận được nhúng vào

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "shards")
RAW_FILE   = os.path.join(os.path.dirname(__file__), "transactions_raw.json")


def generate_accounts(n: int) -> list[dict]:
    """Tạo danh sách tài khoản."""
    accounts = []
    for i in range(n):
        accounts.append({
            "account_id": f"ACC_{i:03d}",
            "owner":      f"Owner_{i}",
            "balance":    round(random.uniform(1_000, 100_000), 2),
            "risk_score": round(random.uniform(0, 1), 3),
        })
    return accounts


def generate_normal_transactions(accounts: list[dict], n: int) -> list[dict]:
    """Tạo giao dịch bình thường (không tạo vòng tròn)."""
    txns = []
    ids  = [a["account_id"] for a in accounts]
    tx_id = 0
    for _ in range(n):
        src, dst = random.sample(ids, 2)
        txns.append({
            "tx_id":  f"TX_{tx_id:04d}",
            "from":   src,
            "to":     dst,
            "amount": round(random.uniform(100, 10_000), 2),
            "is_fraud_edge": False,
        })
        tx_id += 1
    return txns, tx_id


def generate_fraud_cycles(accounts: list[dict], num_rings: int, start_tx_id: int) -> list[dict]:
    """
    Tạo các vòng gian lận: A -> B -> C -> D -> A
    Đây chính là pattern cần detect.
    """
    ids    = [a["account_id"] for a in accounts]
    txns   = []
    cycles = []
    tx_id  = start_tx_id

    for ring_idx in range(num_rings):
        # Chọn 4 tài khoản không trùng nhau
        members = random.sample(ids, 4)
        cycle_edges = []

        # Tạo vòng: members[0]->members[1]->members[2]->members[3]->members[0]
        for i in range(4):
            src = members[i]
            dst = members[(i + 1) % 4]
            edge = {
                "tx_id":         f"TX_{tx_id:04d}",
                "from":          src,
                "to":            dst,
                "amount":        round(random.uniform(5_000, 50_000), 2),
                "is_fraud_edge": True,
                "ring_id":       f"RING_{ring_idx}",
            }
            txns.append(edge)
            cycle_edges.append(edge["tx_id"])
            tx_id += 1

        cycles.append({
            "ring_id":  f"RING_{ring_idx}",
            "members":  members,
            "tx_ids":   cycle_edges,
        })
        print(f"  [INJECTED] Fraud ring RING_{ring_idx}: {' -> '.join(members)} -> {members[0]}")

    return txns, cycles


def main():
    print("=" * 60)
    print("Generating Financial Transaction Dataset...")
    print("=" * 60)

    accounts = generate_accounts(NUM_ACCOUNTS)
    print(f"  Created {len(accounts)} accounts.")

    normal_txns, next_id = generate_normal_transactions(accounts, NUM_NORMAL_TX)
    print(f"  Created {len(normal_txns)} normal transactions.")

    fraud_txns, injected_cycles = generate_fraud_cycles(accounts, NUM_FRAUD_RINGS, next_id)
    print(f"  Injected {NUM_FRAUD_RINGS} fraud rings ({len(fraud_txns)} fraud edges).")

    all_txns = normal_txns + fraud_txns
    random.shuffle(all_txns)  # Trộn để fraud không dễ tìm

    dataset = {
        "accounts":        accounts,
        "transactions":    all_txns,
        "ground_truth":    injected_cycles,   # Để kiểm tra kết quả
    }

    os.makedirs(os.path.dirname(RAW_FILE), exist_ok=True)
    with open(RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"\n  Raw dataset saved → {RAW_FILE}")
    print(f"  Total transactions: {len(all_txns)}")
    print("=" * 60)
    return dataset


if __name__ == "__main__":
    main()
