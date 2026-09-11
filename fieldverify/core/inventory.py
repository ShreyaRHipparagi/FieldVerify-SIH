"""
FieldVerify Station Reagent Inventory & Expiry Auto-Alarm Tracker
Tracks chemical reagent pouches, batch numbers, physical units in stock,
expiry countdowns, and triggers automatic replenishment alarms.
"""

import sqlite3
import os
from datetime import datetime, timezone, timedelta

INVENTORY_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fieldverify_ledger.db")
_INITIALIZED_INVENTORY_DBS = set()


def init_inventory_db(db_path=INVENTORY_DB_PATH):
    """Creates the reagent inventory table and seeds initial stock if empty."""
    abs_path = os.path.abspath(db_path)
    if abs_path in _INITIALIZED_INVENTORY_DBS:
        return

    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS reagent_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reagent_code TEXT UNIQUE NOT NULL,
                reagent_name TEXT NOT NULL,
                target_drug TEXT NOT NULL,
                batch_lot TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                quantity_in_stock INTEGER NOT NULL,
                min_threshold INTEGER DEFAULT 5,
                station_id TEXT NOT NULL,
                last_inspected TEXT NOT NULL
            );
            """)

            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM reagent_inventory")
            count = cursor.fetchone()[0]

            if count == 0:
                today = datetime.now(timezone.utc)
                exp_valid = (today + timedelta(days=365)).strftime("%Y-%m-%d")
                exp_critical = (today + timedelta(days=12)).strftime("%Y-%m-%d")
                exp_passed = (today - timedelta(days=15)).strftime("%Y-%m-%d")

                initial_stock = [
                    ("SCOTT_REAGENT", "Scott Reagent (Cobalt Thiocyanate)", "Cocaine HCl", "SC-2026-0819", exp_valid, 28, 5, "STATION-GHY-CENTRAL", today.strftime("%Y-%m-%d")),
                    ("MARQUIS_OPIATE", "Marquis Reagent (Opiate)", "Heroin / Morphine", "MQ-2026-0412", exp_valid, 15, 5, "STATION-GHY-CENTRAL", today.strftime("%Y-%m-%d")),
                    ("MARQUIS_AMPHETAMINE", "Marquis Reagent (Amphetamine)", "Methamphetamine", "MA-2026-0105", exp_critical, 3, 5, "STATION-GHY-CENTRAL", today.strftime("%Y-%m-%d")),
                    ("DUQUENOIS_LEVINE", "Duquenois-Levine Reagent", "Cannabis / THC", "DL-2025-1102", exp_passed, 1, 5, "STATION-GHY-CENTRAL", today.strftime("%Y-%m-%d")),
                ]

                cursor.executemany("""
                INSERT INTO reagent_inventory (
                    reagent_code, reagent_name, target_drug, batch_lot, expiry_date,
                    quantity_in_stock, min_threshold, station_id, last_inspected
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, initial_stock)

        _INITIALIZED_INVENTORY_DBS.add(abs_path)
    finally:
        conn.close()


def get_inventory_status(db_path=INVENTORY_DB_PATH):
    """
    Returns inventory items with calculated status:
    - 'OK'
    - 'EXPIRING_SOON' (<= 30 days)
    - 'EXPIRED' (< 0 days)
    - 'LOW_STOCK' (quantity <= min_threshold)
    """
    init_inventory_db(db_path)
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reagent_inventory ORDER BY expiry_date ASC")
        rows = cursor.fetchall()
    finally:
        conn.close()

    today = datetime.now(timezone.utc).date()
    items = []

    for row in rows:
        item = dict(row)
        try:
            exp_date = datetime.strptime(str(item["expiry_date"]).strip(), "%Y-%m-%d").date()
            days_left = (exp_date - today).days
        except (ValueError, TypeError):
            days_left = 999

        item["days_left"] = days_left

        alerts = []
        if days_left < 0:
            alerts.append("EXPIRED")
        elif days_left <= 30:
            alerts.append("EXPIRING_SOON")

        if item["quantity_in_stock"] <= item["min_threshold"]:
            alerts.append("LOW_STOCK")

        if not alerts:
            alerts.append("OPTIMAL")

        item["status_flags"] = alerts
        items.append(item)

    return items


def record_reagent_usage(reagent_code, db_path=INVENTORY_DB_PATH):
    """Decrements stock count by 1 upon performing a field test."""
    init_inventory_db(db_path)
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        with conn:
            conn.execute(
                "UPDATE reagent_inventory SET quantity_in_stock = MAX(0, quantity_in_stock - 1) WHERE reagent_code = ?",
                (str(reagent_code),)
            )
    finally:
        conn.close()
