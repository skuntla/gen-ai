#!/usr/bin/env python3
"""
Seed data/sample.db for Phase 04 text-to-SQL tool.

Loads curated CSVs from data/seeds/ and optionally fetches recent OHLC
from yfinance (INFY.NS). Run offline before using the agent:

    python scripts/seed_sample_db.py
    python scripts/seed_sample_db.py --no-prices   # skip yfinance
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = ROOT / "data" / "seeds"
DEFAULT_DB = ROOT / "data" / "sample.db"

FINANCIALS_CSV = SEEDS_DIR / "infosys_financials.csv"
SHAREHOLDING_CSV = SEEDS_DIR / "infosys_shareholding.csv"

YFINANCE_SYMBOL = "INFY.NS"
YFINANCE_DAYS = 252


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS financials (
            symbol              TEXT NOT NULL,
            fiscal_year         TEXT NOT NULL,
            revenue_cr          REAL,
            operating_margin_pct REAL,
            net_margin_pct      REAL,
            roe_pct             REAL,
            debt_to_equity      REAL,
            PRIMARY KEY (symbol, fiscal_year)
        );

        CREATE TABLE IF NOT EXISTS shareholding (
            symbol       TEXT NOT NULL,
            quarter      TEXT NOT NULL,
            promoter_pct REAL,
            fii_pct      REAL,
            PRIMARY KEY (symbol, quarter)
        );

        CREATE TABLE IF NOT EXISTS daily_prices (
            symbol     TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            open       REAL,
            high       REAL,
            low        REAL,
            close      REAL,
            volume     INTEGER,
            PRIMARY KEY (symbol, trade_date)
        );

        CREATE TABLE IF NOT EXISTS _meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def _seed_financials(conn: sqlite3.Connection) -> int:
    rows = _load_csv(FINANCIALS_CSV)
    conn.execute("DELETE FROM financials WHERE symbol = 'INFY'")
    conn.executemany(
        """
        INSERT INTO financials (
            symbol, fiscal_year, revenue_cr, operating_margin_pct,
            net_margin_pct, roe_pct, debt_to_equity
        ) VALUES (
            :symbol, :fiscal_year, :revenue_cr, :operating_margin_pct,
            :net_margin_pct, :roe_pct, :debt_to_equity
        )
        """,
        [
            {
                "symbol": r["symbol"],
                "fiscal_year": r["fiscal_year"],
                "revenue_cr": float(r["revenue_cr"]),
                "operating_margin_pct": float(r["operating_margin_pct"]),
                "net_margin_pct": float(r["net_margin_pct"]),
                "roe_pct": float(r["roe_pct"]),
                "debt_to_equity": float(r["debt_to_equity"]),
            }
            for r in rows
        ],
    )
    return len(rows)


def _seed_shareholding(conn: sqlite3.Connection) -> int:
    rows = _load_csv(SHAREHOLDING_CSV)
    conn.execute("DELETE FROM shareholding WHERE symbol = 'INFY'")
    conn.executemany(
        """
        INSERT INTO shareholding (symbol, quarter, promoter_pct, fii_pct)
        VALUES (:symbol, :quarter, :promoter_pct, :fii_pct)
        """,
        [
            {
                "symbol": r["symbol"],
                "quarter": r["quarter"],
                "promoter_pct": float(r["promoter_pct"]),
                "fii_pct": float(r["fii_pct"]),
            }
            for r in rows
        ],
    )
    return len(rows)


def _seed_daily_prices(conn: sqlite3.Connection) -> int:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(
            "yfinance is required for daily_prices. "
            "Install with: pip install yfinance  OR  run with --no-prices"
        ) from exc

    ticker = yf.Ticker(YFINANCE_SYMBOL)
    hist = ticker.history(period=f"{YFINANCE_DAYS}d", auto_adjust=False)
    if hist.empty:
        raise RuntimeError(f"No price history returned for {YFINANCE_SYMBOL}")

    conn.execute("DELETE FROM daily_prices WHERE symbol = 'INFY'")
    records: list[tuple] = []
    for idx, row in hist.iterrows():
        trade_date = idx.strftime("%Y-%m-%d")
        records.append(
            (
                "INFY",
                trade_date,
                round(float(row["Open"]), 2),
                round(float(row["High"]), 2),
                round(float(row["Low"]), 2),
                round(float(row["Close"]), 2),
                int(row["Volume"]),
            )
        )

    conn.executemany(
        """
        INSERT INTO daily_prices (symbol, trade_date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )
    return len(records)


def seed(db_path: Path, *, include_prices: bool = True) -> dict:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        _create_schema(conn)
        n_fin = _seed_financials(conn)
        n_sh = _seed_shareholding(conn)
        n_px = 0
        if include_prices:
            n_px = _seed_daily_prices(conn)

        conn.execute(
            "INSERT OR REPLACE INTO _meta (key, value) VALUES (?, ?)",
            ("seeded_at", datetime.now(timezone.utc).isoformat()),
        )
        conn.execute(
            "INSERT OR REPLACE INTO _meta (key, value) VALUES (?, ?)",
            ("yfinance_symbol", YFINANCE_SYMBOL if include_prices else "skipped"),
        )
        conn.commit()

    return {
        "db_path": str(db_path),
        "financials": n_fin,
        "shareholding": n_sh,
        "daily_prices": n_px,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Phase 04 sample.db from CSV + yfinance.")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"Output SQLite path (default: {DEFAULT_DB.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--no-prices",
        action="store_true",
        help="Skip daily_prices (no yfinance network call)",
    )
    args = parser.parse_args()

    try:
        stats = seed(args.db, include_prices=not args.no_prices)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Seeded {stats['db_path']}")
    print(f"  financials     : {stats['financials']} rows")
    print(f"  shareholding   : {stats['shareholding']} rows")
    print(f"  daily_prices   : {stats['daily_prices']} rows")


if __name__ == "__main__":
    main()
