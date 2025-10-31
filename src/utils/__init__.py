"""Logging utilities for trading operations."""

import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from ..cache.db_manager import DatabaseManager
from ..config import get_config


class TradingLogger:
    """Dual logging for trading operations - database + text file."""

    def __init__(self):
        """Initialize trading logger."""
        self.config = get_config()
        self.db = DatabaseManager()
        self._setup_file_logger()

    def _setup_file_logger(self):
        """Setup file logger for trading operations."""
        log_dir = self.config.log_dir
        log_file = log_dir / "trading_operations.log"

        self.file_logger = logging.getLogger("trading_ops")
        self.file_logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if not self.file_logger.handlers:
            handler = RotatingFileHandler(
                log_file,
                maxBytes=self.config.log_max_bytes,
                backupCount=self.config.log_backup_count,
            )
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.file_logger.addHandler(handler)

    def log_order_operation(
        self,
        operation: str,
        symbol: str,
        reason: str,
        order_type: Optional[str] = None,
        action: Optional[str] = None,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        risk_checks: Optional[Dict[str, Any]] = None,
        result: str = "pending",
        order_id: Optional[str] = None,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Log a trading operation to both database and text file.

        Args:
            operation: Operation type (place_order, modify_order, cancel_order)
            symbol: Stock symbol
            reason: AI-provided reason for the operation (required)
            order_type: Order type (MKT, LMT, STP, STP LMT)
            action: BUY or SELL
            quantity: Number of shares/contracts
            price: Limit price
            stop_loss: Stop loss price
            take_profit: Take profit price
            risk_checks: Risk check results
            result: Operation result (success, failed, pending)
            order_id: IB order ID
            error_message: Error message if failed
            additional_data: Any additional data

        Returns:
            Database log entry ID
        """
        # 1. Log to database
        log_id = self.db.log_trading_operation(
            operation=operation,
            symbol=symbol,
            reason=reason,
            order_type=order_type,
            action=action,
            quantity=quantity,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_checks=risk_checks,
            result=result,
            order_id=order_id,
            error_message=error_message,
            additional_data=additional_data,
        )

        # 2. Log to text file (human-readable format)
        log_message = self._format_log_message(
            operation=operation,
            symbol=symbol,
            reason=reason,
            order_type=order_type,
            action=action,
            quantity=quantity,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_checks=risk_checks,
            result=result,
            order_id=order_id,
            error_message=error_message,
            additional_data=additional_data,
        )

        if result == "failed":
            self.file_logger.error(log_message)
        elif result == "success":
            self.file_logger.info(log_message)
        else:
            self.file_logger.warning(log_message)

        return log_id

    def _format_log_message(
        self,
        operation: str,
        symbol: str,
        reason: str,
        **kwargs,
    ) -> str:
        """Format log message for text file.

        Args:
            operation: Operation type
            symbol: Symbol
            reason: Reason for operation
            **kwargs: Additional parameters

        Returns:
            Formatted log message
        """
        lines = [
            f"{'=' * 80}",
            f"OPERATION: {operation.upper()}",
            f"SYMBOL: {symbol}",
            f"REASON: {reason}",
        ]

        # Add order details
        if kwargs.get("order_type"):
            lines.append(f"ORDER TYPE: {kwargs['order_type']}")
        if kwargs.get("action"):
            lines.append(f"ACTION: {kwargs['action']}")
        if kwargs.get("quantity"):
            lines.append(f"QUANTITY: {kwargs['quantity']}")
        if kwargs.get("price"):
            lines.append(f"PRICE: ${kwargs['price']:.2f}")
        if kwargs.get("stop_loss"):
            lines.append(f"STOP LOSS: ${kwargs['stop_loss']:.2f}")
        if kwargs.get("take_profit"):
            lines.append(f"TAKE PROFIT: ${kwargs['take_profit']:.2f}")

        # Add risk checks
        if kwargs.get("risk_checks"):
            lines.append("\nRISK CHECKS:")
            for check_name, check_result in kwargs["risk_checks"].items():
                if isinstance(check_result, dict):
                    level = check_result.get("level", "unknown")
                    message = check_result.get("message", "")
                    lines.append(f"  - {check_name}: [{level.upper()}] {message}")
                else:
                    lines.append(f"  - {check_name}: {check_result}")

        # Add result
        result = kwargs.get("result", "pending")
        lines.append(f"\nRESULT: {result.upper()}")

        if kwargs.get("order_id"):
            lines.append(f"ORDER ID: {kwargs['order_id']}")

        if kwargs.get("error_message"):
            lines.append(f"ERROR: {kwargs['error_message']}")

        # Add additional data
        if kwargs.get("additional_data"):
            lines.append(f"\nADDITIONAL DATA:")
            lines.append(json.dumps(kwargs["additional_data"], indent=2))

        lines.append(f"{'=' * 80}\n")

        return "\n".join(lines)

    def log_info(self, message: str):
        """Log informational message."""
        self.file_logger.info(message)

    def log_warning(self, message: str):
        """Log warning message."""
        self.file_logger.warning(message)

    def log_error(self, message: str):
        """Log error message."""
        self.file_logger.error(message)


# Global logger instance
_trading_logger: Optional[TradingLogger] = None


def get_trading_logger() -> TradingLogger:
    """Get or create the global trading logger instance."""
    global _trading_logger
    if _trading_logger is None:
        _trading_logger = TradingLogger()
    return _trading_logger
