"""Configuration management for IB MCP Server."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # IB Gateway Connection
    ib_host: str = Field(default="127.0.0.1", description="IB Gateway host")
    ib_port: int = Field(default=7497, description="IB Gateway port")
    ib_client_id: int = Field(default=1, description="IB client ID")
    ib_account: str = Field(default="", description="IB account number")

    # Risk Management
    risk_max_single_position_pct: float = Field(
        default=20.0, description="Max single position as % of equity"
    )
    risk_max_total_position_pct: float = Field(
        default=85.0, description="Max total position as % of net liquidation"
    )
    risk_max_drawdown_pct: float = Field(
        default=10.0, description="Max drawdown % before forced close"
    )
    risk_max_option_position_pct: float = Field(
        default=10.0, description="Max option position as % of equity"
    )
    risk_allow_margin: bool = Field(default=False, description="Allow margin trading")
    risk_require_stop_loss: bool = Field(default=True, description="Require stop loss on orders")
    risk_sector_concentration_warning: float = Field(
        default=30.0, description="Warn if sector concentration exceeds this %"
    )
    risk_high_volatility_threshold: float = Field(
        default=50.0, description="Warn if implied volatility exceeds this"
    )
    risk_min_liquidity_volume: int = Field(
        default=100000, description="Warn if average volume below this"
    )
    risk_bond_collateral_multiplier: float = Field(
        default=0.95, description="Multiplier for bond collateral (SGOV, etc.)"
    )

    # Cache & Database
    cache_db_path: str = Field(default="./data/trading.db", description="SQLite database path")
    cache_kline_days: int = Field(default=365, description="K-line cache duration in days")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_path: str = Field(default="./logs/", description="Log file directory")
    log_max_bytes: int = Field(default=10485760, description="Max log file size (10MB)")
    log_backup_count: int = Field(default=5, description="Number of backup log files")

    # Timezone
    timezone: str = Field(default="America/New_York", description="Timezone for trading")

    @property
    def db_path(self) -> Path:
        """Get database path as Path object."""
        path = Path(self.cache_db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def log_dir(self) -> Path:
        """Get log directory as Path object."""
        path = Path(self.log_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def validate_ib_config(self) -> bool:
        """Validate IB connection configuration."""
        if not self.ib_account:
            raise ValueError("IB_ACCOUNT must be set in environment")
        if not 1024 <= self.ib_port <= 65535:
            raise ValueError("IB_PORT must be between 1024 and 65535")
        return True


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
        _config.validate_ib_config()
    return _config


def reset_config():
    """Reset configuration (useful for testing)."""
    global _config
    _config = None
