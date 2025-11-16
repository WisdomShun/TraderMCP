"""Database manager for SQLite operations."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..config import get_config


class DatabaseManager:
    """Manages SQLite database for caching and logging."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file. If None, uses config default.
        """
        self.config = get_config()
        self.db_path = db_path or self.config.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # K-line data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kline_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    bar_size TEXT NOT NULL,
                    datetime TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    average REAL,
                    bar_count INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, bar_size, datetime)
                )
            """)

            # Index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_kline_symbol_barsize 
                ON kline_data(symbol, bar_size, datetime)
            """)

            # Trading logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    result TEXT,
                    error_message TEXT,
                    additional_data TEXT
                )
            """)

            # Index for trading logs
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trading_logs_timestamp 
                ON trading_logs(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trading_logs_symbol 
                ON trading_logs(symbol, timestamp DESC)
            """)

            # Option chains cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS option_chains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    contract_symbol TEXT NOT NULL,
                    expiration_date TEXT,
                    strike REAL,
                    option_type TEXT,
                    delta REAL,
                    gamma REAL,
                    theta REAL,
                    vega REAL,
                    rho REAL,
                    implied_volatility REAL,
                    bid REAL,
                    ask REAL,
                    last REAL,
                    volume INTEGER,
                    open_interest INTEGER,
                    last_update TEXT,
                    UNIQUE(contract_symbol)
                )
            """)

            # Index for option chains
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_option_chains_symbol 
                ON option_chains(symbol, expiration_date, strike)
            """)

            conn.commit()

    # ==================== K-line Data Methods ====================

    def save_kline_data(
        self,
        symbol: str,
        bar_size: str,
        bars: List[Tuple[str, float, float, float, float, int, float, int]],
    ) -> int:
        """Save K-line data to database.

        Args:
            symbol: Stock symbol
            bar_size: Bar size (e.g., '1D', '1W', '1M')
            bars: List of (datetime, open, high, low, close, volume, average, bar_count)

        Returns:
            Number of rows inserted
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            inserted = 0

            for bar in bars:
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO kline_data 
                        (symbol, bar_size, datetime, open, high, low, close, volume, average, bar_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (symbol, bar_size, *bar),
                    )
                    inserted += cursor.rowcount
                except sqlite3.IntegrityError:
                    continue

            conn.commit()
            return inserted

    def get_kline_data(
        self,
        symbol: str,
        bar_size: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Get K-line data from database.

        Args:
            symbol: Stock symbol
            bar_size: Bar size (e.g., '1D', '1W', '1M')
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            DataFrame with K-line data
        """
        query = """
            SELECT datetime, open, high, low, close, volume, average, bar_count
            FROM kline_data
            WHERE symbol = ? AND bar_size = ?
        """
        params = [symbol, bar_size]

        if start_date:
            query += " AND datetime >= ?"
            params.append(start_date)
        if end_date:
            query += " AND datetime <= ?"
            params.append(end_date)

        query += " ORDER BY datetime ASC"

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df["datetime"] = pd.to_datetime(df["datetime"])
            return df

    def get_latest_kline_date(self, symbol: str, bar_size: str) -> Optional[str]:
        """Get the latest date for cached K-line data.

        Args:
            symbol: Stock symbol
            bar_size: Bar size

        Returns:
            Latest datetime string or None if no data
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT MAX(datetime) FROM kline_data
                WHERE symbol = ? AND bar_size = ?
                """,
                (symbol, bar_size),
            )
            result = cursor.fetchone()
            return result[0] if result and result[0] else None

    def get_latest_kline_datetime(self, symbol: str, bar_size: str) -> Optional[str]:
        """Get the latest datetime for cached K-line data (alias for get_latest_kline_date).

        Args:
            symbol: Stock symbol
            bar_size: Bar size

        Returns:
            Latest datetime string or None if no data
        """
        return self.get_latest_kline_date(symbol, bar_size)

    # ==================== Trading Logs Methods ====================

    def log_trading_operation(
        self,
        operation: str,
        symbol: str,
        reason: str,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Log a trading operation to database.

        Args:
            operation: Operation type (query, analysis, etc.)
            symbol: Stock symbol
            reason: Reason for the operation (required)
            result: Operation result (success, failed, pending)
            error_message: Error message if failed
            additional_data: Any additional data

        Returns:
            Log entry ID
        """
        timestamp = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO trading_logs 
                (timestamp, operation, symbol, reason, result,
                 error_message, additional_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    operation,
                    symbol,
                    reason,
                    result,
                    error_message,
                    json.dumps(additional_data) if additional_data else None,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_trading_logs(
        self,
        symbol: Optional[str] = None,
        operation: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get trading logs from database.

        Args:
            symbol: Filter by symbol
            operation: Filter by operation type
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            limit: Maximum number of records

        Returns:
            List of log entries
        """
        query = "SELECT * FROM trading_logs WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if operation:
            query += " AND operation = ?"
            params.append(operation)
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            logs = []
            for row in rows:
                log = dict(row)
                # Parse JSON fields
                if log.get("additional_data"):
                    log["additional_data"] = json.loads(log["additional_data"])
                logs.append(log)

            return logs

    # ==================== Option Chains Methods ====================

    def save_option_chain(self, symbol: str, options: List[Dict[str, Any]]) -> int:
        """Save option chain data to database.

        Args:
            symbol: Underlying symbol
            options: List of option contract data

        Returns:
            Number of rows inserted/updated
        """
        timestamp = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            inserted = 0

            for opt in options:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO option_chains 
                    (symbol, contract_symbol, expiration_date, strike, option_type,
                     delta, gamma, theta, vega, rho, implied_volatility,
                     bid, ask, last, volume, open_interest, last_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol,
                        opt.get("contract_symbol"),
                        opt.get("expiration_date"),
                        opt.get("strike"),
                        opt.get("option_type"),
                        opt.get("delta"),
                        opt.get("gamma"),
                        opt.get("theta"),
                        opt.get("vega"),
                        opt.get("rho"),
                        opt.get("implied_volatility"),
                        opt.get("bid"),
                        opt.get("ask"),
                        opt.get("last"),
                        opt.get("volume"),
                        opt.get("open_interest"),
                        timestamp,
                    ),
                )
                inserted += cursor.rowcount

            conn.commit()
            return inserted

    def get_option_chain(
        self, symbol: str, expiration_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get option chain data from database.

        Args:
            symbol: Underlying symbol
            expiration_date: Filter by expiration date

        Returns:
            List of option contracts
        """
        query = "SELECT * FROM option_chains WHERE symbol = ?"
        params = [symbol]

        if expiration_date:
            query += " AND expiration_date = ?"
            params.append(expiration_date)

        query += " ORDER BY expiration_date, strike"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def cleanup_old_data(self, days: int = 365):
        """Clean up old cached data.

        Args:
            days: Keep data newer than this many days
        """
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff.replace(day=cutoff.day - days)
        cutoff_str = cutoff.isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Clean old K-line data (keep configured days)
            cursor.execute(
                "DELETE FROM kline_data WHERE datetime < ?",
                (cutoff_str,),
            )

            # Clean old option chains (keep 30 days)
            option_cutoff = datetime.now().replace(day=datetime.now().day - 30).isoformat()
            cursor.execute(
                "DELETE FROM option_chains WHERE last_update < ?",
                (option_cutoff,),
            )

            conn.commit()
