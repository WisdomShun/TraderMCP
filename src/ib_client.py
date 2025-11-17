"""IB Gateway client wrapper using ib_insync."""

import asyncio
import logging
from typing import List, Optional

from ib_insync import IB, Contract, Stock, Option, BarDataList
from ib_insync import AccountValue, Position, PortfolioItem, OptionChain, OptionComputation, Ticker

from .config import get_config
from .logger import logger


class IBClient:
    """Interactive Brokers client wrapper."""

    def __init__(self):
        """Initialize IB client."""
        self.config = get_config()
        self.ib = IB()
        self.reconnect_task = None
        self._auto_reconnect = True
        # 注册断线事件处理器
        self.ib.disconnectedEvent += self._on_disconnected
        self.ib.connectedEvent += self._on_connected

    def get_ib_port(self) -> int:
        """Get the IB API port based on trading mode."""
        if self.config.trading_mode == "live":
            return self.config.ib_api_port_live
        else:
            return self.config.ib_api_port_paper

    async def connect(self) -> bool:
        """Connect to IB Gateway with retry logic.

        Returns:
            True if connected successfully
        """
        if self.ib.isConnected():
            return True

        retry_delay = 5  # seconds between retries
        attempt = 0

        ib_port = self.get_ib_port()
        
        while True:
            attempt += 1
            try:
                logger.info(
                    f"Connect to IB Gateway at {self.config.ib_host}:{ib_port} (attempt {attempt})"
                )
                await self.ib.connectAsync(
                    host=self.config.ib_host,
                    port=ib_port,
                    clientId=self.config.ib_client_id,
                    account=self.config.ib_account,
                    readonly=True,
                    timeout=20,
                )
                return True
            except Exception as e:
                logger.warning(f"Failed : {e}. Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)

    async def disconnect(self):
        """Disconnect from IB Gateway."""
        # 禁用自动重连
        self._auto_reconnect = False
        
        if self.ib.isConnected():
            self.ib.disconnect()
            logger.info("Disconnected from IB Gateway")

    async def ensure_connected(self):
        """Ensure connection is active, reconnect if needed."""
        if not self.ib.isConnected():
            await self.connect()

    def _on_disconnected(self):
        """Handle disconnection event and trigger reconnection."""
        logger.warning("Connection lost")
        if self.reconnect_task is None and self._auto_reconnect:
            logger.info("Triggering reconnection...")
            self.reconnect_task = asyncio.create_task(self.connect(), name="IBClientReconnectTask")

    def _on_connected(self):
        """Handle connection event."""
        logger.info(f"Connected to IB Gateway at {self.config.ib_host}:{self.get_ib_port()}")
        self._auto_reconnect = True
        if self.reconnect_task is not None:
            self.reconnect_task.cancel()
            self.reconnect_task = None


    # ==================== Contract Creation Helpers ====================

    def create_stock_contract(self, symbol: str, exchange: str = "SMART", currency: str = "USD") -> Contract:
        """Create a stock contract.

        Args:
            symbol: Stock symbol
            exchange: Exchange (default: SMART)
            currency: Currency (default: USD)

        Returns:
            Stock contract
        """
        return Stock(symbol, exchange, currency)

    def create_option_contract(
        self,
        symbol: str,
        expiration: str,
        strike: float,
        right: str,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> Contract:
        """Create an option contract.

        Args:
            symbol: Underlying symbol
            expiration: Expiration date (YYYYMMDD)
            strike: Strike price
            right: 'C' for call, 'P' for put
            exchange: Exchange (default: SMART)
            currency: Currency (default: USD)

        Returns:
            Option contract
        """
        return Option(symbol, expiration, strike, right, exchange, currency)

    async def qualify_contract(self, contract: Contract) -> Optional[Contract]:
        """Qualify a contract with IB.

        Args:
            contract: Contract to qualify

        Returns:
            Qualified contract or None if failed
        """
        await self.ensure_connected()
        try:
            qualified = await self.ib.qualifyContractsAsync(contract)
            return qualified[0] if qualified else None
        except Exception as e:
            logger.error(f"Failed to qualify contract {contract}: {e}")
            return None

    # ==================== Account & Position Methods ====================

    async def get_account_summary(self, account: Optional[str] = None) -> List[AccountValue]:
        """Get account summary with key metrics.

        Args:
            account: Account number (uses config default if None)

        Returns:
            List of AccountValue objects from ib_insync
        """
        await self.ensure_connected()
        account = account or self.config.ib_account
        return self.ib.accountSummary(account)

    async def get_positions(self, account: Optional[str] = None) -> List[Position]:
        """Get current positions.

        Args:
            account: Account number (uses config default if None)

        Returns:
            List of Position objects (basic position info)
        """
        await self.ensure_connected()
        account = account or self.config.ib_account
        return [p for p in self.ib.positions() if p.account == account or account == "All"]

    async def get_portfolio(self, account: Optional[str] = None) -> List[PortfolioItem]:
        """Get portfolio items with market values and P&L.

        Args:
            account: Account number (uses config default if None)

        Returns:
            List of PortfolioItem objects (includes marketValue, unrealizedPNL, etc.)
        """
        await self.ensure_connected()
        account = account or self.config.ib_account
        return [p for p in self.ib.portfolio() if p.account == account or account == "All"]

    # ==================== Market Data Methods ====================

    async def get_historical_data(
        self,
        contract: Contract,
        duration: str = "1 Y",
        bar_size: str = "1 day",
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        end_datetime: Optional[str] = None,
    ) -> BarDataList:
        """Get historical bar data.

        Args:
            contract: Contract
            duration: Duration string (e.g., "1 Y", "6 M", "1 W")
            bar_size: Bar size (e.g., "1 day", "1 hour", "1 min")
            what_to_show: Data type (TRADES, MIDPOINT, BID, ASK)
            use_rth: Use regular trading hours only
            end_datetime: End date/time (default: now)

        Returns:
            List of bars
        """
        await self.ensure_connected()

        try:
            bars = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime=end_datetime or "",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow=what_to_show,
                useRTH=use_rth,
                formatDate=1,
            )
            return bars
        except Exception as e:
            logger.error(f"Failed to get historical data for {contract}: {e}")
            return []

    async def get_ticker(self, contract: Contract, snapshot: bool = True, timeout: float = 5.0) -> Optional[Ticker]:
        """Get ticker data (market data snapshot).

        Args:
            contract: Contract
            snapshot: If True, returns snapshot and unsubscribes
            timeout: Timeout in seconds (default: 5.0)

        Returns:
            Ticker object or None
        """
        await self.ensure_connected()

        try:
            if snapshot:
                ticker = self.ib.reqMktData(contract, snapshot=True)
                
                # Wait for ticker to be updated using event mechanism
                try:
                    await asyncio.wait_for(ticker.updateEvent, timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for ticker data for {contract}")
                
                self.ib.cancelMktData(contract)
                return ticker
            else:
                return self.ib.reqMktData(contract, snapshot=False)
        except Exception as e:
            logger.error(f"Failed to get ticker for {contract}: {e}")
            return None

    async def get_option_chains(
        self, symbol: str, exchange: str = "SMART"
    ) -> Optional[List[OptionChain]]:
        """Get option chains for a symbol.

        Args:
            symbol: Underlying symbol
            exchange: Exchange

        Returns:
            Option chain object or None
        """
        await self.ensure_connected()

        try:
            contract = Stock(symbol, exchange, "USD")
            qualified = await self.qualify_contract(contract)
            if not qualified:
                return None

            chains = await self.ib.reqSecDefOptParamsAsync(
                qualified.symbol,
                "",
                qualified.secType,
                qualified.conId,
            )
            return chains
        except Exception as e:
            logger.error(f"Failed to get option chains for {symbol}: {e}")
            return None

    async def get_option_greeks(self, contract: Contract, timeout: float = 5.0) -> Optional[OptionComputation]:
        """Get option Greeks.

        Args:
            contract: Option contract
            timeout: Timeout in seconds (default: 5.0)

        Returns:
            Dictionary with Greeks or None
        """
        await self.ensure_connected()

        try:
            ticker = self.ib.reqMktData(contract, genericTickList="106", snapshot=False)
            
            # Wait for ticker to be updated with Greeks data using event mechanism
            try:
                await asyncio.wait_for(ticker.updateEvent, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for Greeks data for {contract}")
            
            self.ib.cancelMktData(contract)

            if ticker:
                return ticker.modelGreeks
            return None
        except Exception as e:
            logger.error(f"Failed to get Greeks for {contract}: {e}")
            return None

    # ==================== Fundamental Data Methods ====================

    async def get_fundamental_data(
        self, contract: Contract, report_type: str = "ReportsFinSummary"
    ) -> Optional[str]:
        """Get fundamental data for a contract.

        Args:
            contract: Stock contract
            report_type: Type of report (ReportsFinSummary, ReportSnapshot, etc.)

        Returns:
            XML string with fundamental data or None
        """
        await self.ensure_connected()

        try:
            data = await self.ib.reqFundamentalDataAsync(contract, report_type)
            return data
        except Exception as e:
            logger.error(f"Failed to get fundamental data for {contract}: {e}")
            return None

    # ==================== Utility Methods ====================

    def is_connected(self) -> bool:
        """Check if connected to IB Gateway.

        Returns:
            True if connected
        """
        return self.ib.isConnected()

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.disconnect()


# Global client instance
_client: Optional[IBClient] = None


def get_ib_client() -> IBClient:
    """Get or create the global IB client instance."""
    global _client
    if _client is None:
        _client = IBClient()
    return _client
