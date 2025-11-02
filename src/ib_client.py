"""IB Gateway client wrapper using ib_insync."""

import asyncio
import logging
from typing import List, Optional

from ib_insync import IB, Contract, Stock, Option, Order, Trade, BarDataList
from ib_insync import AccountValue, Position, PortfolioItem, OptionChain, OptionComputation, Ticker

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
        return [p for p in self.ib.positions() if p.account == account]

    async def get_portfolio(self, account: Optional[str] = None) -> List[PortfolioItem]:
        """Get portfolio items with market values and P&L.

        Args:
            account: Account number (uses config default if None)

        Returns:
            List of PortfolioItem objects (includes marketValue, unrealizedPNL, etc.)
        """
        await self.ensure_connected()
        account = account or self.config.ib_account
        return [p for p in self.ib.portfolio() if p.account == account]

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

    async def place_order(self, contract: Contract, order: Order, timeout: float = 5.0) -> Trade:
        """Place an order.

        Args:
            contract: Contract to trade
            order: Order details
            timeout: Timeout in seconds (default: 5.0)

        Returns:
            Trade object
        """
        await self.ensure_connected()
        trade = self.ib.placeOrder(contract, order)

        # Wait for order status update using event mechanism
        try:
            await asyncio.wait_for(trade.statusEvent, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for order status for {contract}")
        
        return trade

    async def modify_order(self, trade: Trade, order: Order, timeout: float = 5.0) -> Trade:
        """Modify an existing order.

        Args:
            trade: Existing trade
            order: Modified order
            timeout: Timeout in seconds (default: 5.0)

        Returns:
            Updated trade object
        """
        await self.ensure_connected()
        self.ib.placeOrder(trade.contract, order)
        
        # Wait for order status update using event mechanism
        try:
            await asyncio.wait_for(trade.statusEvent, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for order modification status")
        
        return trade

    async def cancel_order(self, order: Order, timeout: float = 5.0) -> bool:
        """Cancel an order.

        Args:
            order: Order to cancel
            timeout: Timeout in seconds (default: 5.0)

        Returns:
            True if cancelled successfully
        """
        await self.ensure_connected()
        try:
            self.ib.cancelOrder(order)
            
            # Find the trade for this order to wait for status update
            trade = next((t for t in self.ib.trades() if t.order.orderId == order.orderId), None)
            if trade:
                try:
                    await asyncio.wait_for(trade.statusEvent, timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for order cancellation status")
            
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order.orderId}: {e}")
            return False

    # ==================== Convenience Order Methods ====================

    async def place_simple_order(
        self,
        contract: Contract,
        action: str,
        quantity: int,
        order_type: str = "MKT",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        timeout: float = 5.0
    ) -> Optional[Trade]:
        """Place a simple order with common parameters.

        Args:
            contract: Contract to trade
            action: 'BUY' or 'SELL'
            quantity: Number of shares/contracts
            order_type: 'MKT', 'LMT', 'STP', 'STP LMT'
            limit_price: Limit price (required for LMT and STP LMT orders)
            stop_price: Stop price (required for STP and STP LMT orders)
            timeout: Timeout in seconds (default: 5.0)

        Returns:
            Trade object or None if failed
        """
        from ib_insync import MarketOrder, LimitOrder, StopOrder, StopLimitOrder

        # Create order based on type
        if order_type == "MKT":
            order = MarketOrder(action, quantity)
        elif order_type == "LMT":
            if limit_price is None:
                logger.error("Limit price required for limit order")
                return None
            order = LimitOrder(action, quantity, limit_price)
        elif order_type == "STP":
            if stop_price is None:
                logger.error("Stop price required for stop order")
                return None
            order = StopOrder(action, quantity, stop_price)
        elif order_type == "STP LMT":
            if limit_price is None or stop_price is None:
                logger.error("Both limit and stop price required for stop-limit order")
                return None
            order = StopLimitOrder(action, quantity, stop_price, limit_price)
        else:
            logger.error(f"Unsupported order type: {order_type}")
            return None

        return await self.place_order(contract, order, timeout)

    async def place_bracket_order(
        self,
        contract: Contract,
        action: str,
        quantity: int,
        entry_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        timeout: float = 5.0
    ) -> Optional[List[Trade]]:
        """Place a bracket order (entry + stop loss + take profit).

        Args:
            contract: Contract to trade
            action: 'BUY' or 'SELL'
            quantity: Number of shares/contracts
            entry_price: Entry limit price (None for market order)
            stop_loss_price: Stop loss price
            take_profit_price: Take profit price
            timeout: Timeout in seconds (default: 5.0)

        Returns:
            List of Trade objects [parent, stop_loss, take_profit] or None
        """
        from ib_insync import MarketOrder, LimitOrder, Order

        await self.ensure_connected()

        try:
            # Create parent order
            if entry_price:
                parent = LimitOrder(action, quantity, entry_price)
            else:
                parent = MarketOrder(action, quantity)

            parent.transmit = False  # Don't transmit until children are set

            # Determine child action (opposite of parent)
            child_action = 'SELL' if action == 'BUY' else 'BUY'

            # Create take profit order
            take_profit = None
            if take_profit_price:
                take_profit = LimitOrder(child_action, quantity, take_profit_price)
                take_profit.parentId = parent.orderId
                take_profit.transmit = False

            # Create stop loss order
            stop_loss = None
            if stop_loss_price:
                from ib_insync import StopOrder
                stop_loss = StopOrder(child_action, quantity, stop_loss_price)
                stop_loss.parentId = parent.orderId
                stop_loss.transmit = True  # Transmit all when last one is set

            # If no children, just transmit parent
            if not take_profit and not stop_loss:
                parent.transmit = True
                trade = await self.place_order(contract, parent, timeout)
                return [trade] if trade else None

            # Place orders
            trades = []
            parent_trade = self.ib.placeOrder(contract, parent)
            trades.append(parent_trade)

            if take_profit:
                take_profit.parentId = parent_trade.order.orderId
                tp_trade = self.ib.placeOrder(contract, take_profit)
                trades.append(tp_trade)

            if stop_loss:
                stop_loss.parentId = parent_trade.order.orderId
                if not take_profit:
                    stop_loss.transmit = True
                sl_trade = self.ib.placeOrder(contract, stop_loss)
                trades.append(sl_trade)
            elif take_profit:
                # If no stop loss, make sure take profit transmits
                take_profit.transmit = True

            # Wait for parent order status
            try:
                await asyncio.wait_for(parent_trade.statusEvent, timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for bracket order status")

            return trades

        except Exception as e:
            logger.error(f"Failed to place bracket order: {e}")
            return None

    async def modify_simple_order(
        self,
        trade: Trade,
        new_quantity: Optional[int] = None,
        new_price: Optional[float] = None,
        timeout: float = 5.0
    ) -> bool:
        """Modify an existing order with simple parameters.

        Args:
            trade: Existing trade to modify
            new_quantity: New quantity (None to keep current)
            new_price: New price (None to keep current)
            timeout: Timeout in seconds (default: 5.0)

        Returns:
            True if successful
        """
        try:
            # Clone the order
            order = trade.order
            
            # Modify parameters
            if new_quantity is not None:
                order.totalQuantity = new_quantity
            if new_price is not None:
                if hasattr(order, 'lmtPrice'):
                    order.lmtPrice = new_price
                elif hasattr(order, 'auxPrice'):
                    order.auxPrice = new_price

            # Place modified order
            await self.modify_order(trade, order, timeout)
            return True
        except Exception as e:
            logger.error(f"Failed to modify order: {e}")
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
