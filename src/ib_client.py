"""IB Gateway client wrapper using ib_insync."""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from ib_insync import IB, Contract, Stock, Option, Order, Trade, BarDataList
from ib_insync import util

from .config import get_config

logger = logging.getLogger(__name__)


class IBClient:
    """Interactive Brokers client wrapper."""

    def __init__(self):
        """Initialize IB client."""
        self.config = get_config()
        self.ib = IB()
        self._connected = False

    async def connect(self) -> bool:
        """Connect to IB Gateway.

        Returns:
            True if connected successfully
        """
        if self._connected:
            return True

        try:
            await self.ib.connectAsync(
                host=self.config.ib_host,
                port=self.config.ib_port,
                clientId=self.config.ib_client_id,
                timeout=20,
            )
            self._connected = True
            logger.info(
                f"Connected to IB Gateway at {self.config.ib_host}:{self.config.ib_port}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IB Gateway: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from IB Gateway."""
        if self._connected:
            self.ib.disconnect()
            self._connected = False
            logger.info("Disconnected from IB Gateway")

    async def ensure_connected(self):
        """Ensure connection is active, reconnect if needed."""
        if not self._connected or not self.ib.isConnected():
            await self.connect()

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

    async def get_account_values(self, account: Optional[str] = None) -> List:
        """Get account values.

        Args:
            account: Account number (uses config default if None)

        Returns:
            List of account values
        """
        await self.ensure_connected()
        account = account or self.config.ib_account
        return self.ib.accountValues(account)

    async def get_account_summary(self, account: Optional[str] = None) -> dict:
        """Get account summary with key metrics.

        Args:
            account: Account number (uses config default if None)

        Returns:
            Dictionary with account metrics
        """
        await self.ensure_connected()
        account = account or self.config.ib_account

        summary = {}
        for item in self.ib.accountSummary(account):
            summary[item.tag] = {
                "value": item.value,
                "currency": item.currency,
                "account": item.account,
            }

        return summary

    async def get_positions(self, account: Optional[str] = None) -> List:
        """Get current positions.

        Args:
            account: Account number (uses config default if None)

        Returns:
            List of positions
        """
        await self.ensure_connected()
        account = account or self.config.ib_account
        return [p for p in self.ib.positions() if p.account == account]

    # ==================== Order Methods ====================

    async def get_open_orders(self) -> List[Trade]:
        """Get all open orders.

        Returns:
            List of open trades
        """
        await self.ensure_connected()
        return self.ib.openTrades()

    async def get_trades(self) -> List[Trade]:
        """Get all trades (filled and open).

        Returns:
            List of trades
        """
        await self.ensure_connected()
        return self.ib.trades()

    async def place_order(self, contract: Contract, order: Order) -> Trade:
        """Place an order.

        Args:
            contract: Contract to trade
            order: Order details

        Returns:
            Trade object
        """
        await self.ensure_connected()
        trade = self.ib.placeOrder(contract, order)

        # Wait for order to be submitted
        await asyncio.sleep(0.5)
        return trade

    async def modify_order(self, trade: Trade, order: Order) -> Trade:
        """Modify an existing order.

        Args:
            trade: Existing trade
            order: Modified order

        Returns:
            Updated trade object
        """
        await self.ensure_connected()
        self.ib.placeOrder(trade.contract, order)
        await asyncio.sleep(0.5)
        return trade

    async def cancel_order(self, order: Order) -> bool:
        """Cancel an order.

        Args:
            order: Order to cancel

        Returns:
            True if cancelled successfully
        """
        await self.ensure_connected()
        try:
            self.ib.cancelOrder(order)
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order.orderId}: {e}")
            return False

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

    async def get_ticker(self, contract: Contract, snapshot: bool = True) -> Optional:
        """Get ticker data (market data snapshot).

        Args:
            contract: Contract
            snapshot: If True, returns snapshot and unsubscribes

        Returns:
            Ticker object or None
        """
        await self.ensure_connected()

        try:
            if snapshot:
                self.ib.reqMktData(contract, snapshot=True)
                await asyncio.sleep(2)  # Wait for data
                ticker = self.ib.ticker(contract)
                self.ib.cancelMktData(contract)
                return ticker
            else:
                return self.ib.reqMktData(contract, snapshot=False)
        except Exception as e:
            logger.error(f"Failed to get ticker for {contract}: {e}")
            return None

    async def get_option_chains(
        self, symbol: str, exchange: str = "SMART"
    ) -> Optional[object]:
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

    async def get_option_greeks(self, contract: Contract) -> Optional[dict]:
        """Get option Greeks.

        Args:
            contract: Option contract

        Returns:
            Dictionary with Greeks or None
        """
        await self.ensure_connected()

        try:
            self.ib.reqMktData(contract, genericTickList="106", snapshot=False)
            await asyncio.sleep(2)
            ticker = self.ib.ticker(contract)
            self.ib.cancelMktData(contract)

            if ticker and ticker.modelGreeks:
                greeks = ticker.modelGreeks
                return {
                    "delta": greeks.delta,
                    "gamma": greeks.gamma,
                    "theta": greeks.theta,
                    "vega": greeks.vega,
                    "implied_volatility": ticker.impliedVolatility,
                }
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
        return self._connected and self.ib.isConnected()

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
