"""Risk management engine for trading operations."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

from ..config import get_config

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk check severity levels."""
    PASS = "pass"
    WARNING = "warning"
    BLOCK = "block"


@dataclass
class RiskCheckResult:
    """Result of a risk check."""
    check_name: str
    level: RiskLevel
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_name": self.check_name,
            "level": self.level.value,
            "message": self.message,
            "details": self.details or {},
        }


class RiskManager:
    """Manages risk checks for trading operations based on Charlie Munger's principles."""

    def __init__(self):
        """Initialize risk manager."""
        self.config = get_config()

    def check_all(
        self,
        operation: str,
        symbol: str,
        action: str,
        quantity: int,
        price: Optional[float],
        stop_loss: Optional[float],
        account_summary: Dict[str, Any],
        current_positions: List[Any],
        contract_type: str = "STK",
        option_details: Optional[Dict[str, Any]] = None,
    ) -> List[RiskCheckResult]:
        """Run all risk checks for a trading operation.

        Args:
            operation: Operation type (place_order, modify_order)
            symbol: Symbol to trade
            action: BUY or SELL
            quantity: Quantity
            price: Order price (None for market orders)
            stop_loss: Stop loss price
            account_summary: Account summary data
            current_positions: Current positions
            contract_type: STK, OPT, etc.
            option_details: Option-specific details

        Returns:
            List of risk check results
        """
        results = []

        # Common checks for all orders
        if operation == "place_order":
            # 1. Stop loss requirement (Munger: Avoid losses)
            if contract_type == "STK":
                results.append(self._check_stop_loss(action, stop_loss))

            # 2. Margin trading check (Munger: Avoid leverage)
            results.append(self._check_margin_usage(account_summary))

            # 3. Position size check (Munger: Diversification)
            results.append(
                self._check_position_size(
                    symbol, action, quantity, price, account_summary, current_positions
                )
            )

            # 4. Total position limit (Munger: Risk control)
            results.append(
                self._check_total_position_limit(
                    action, quantity, price, account_summary, current_positions
                )
            )

            # 5. Volatility check (Warning only)
            results.append(self._check_volatility(symbol, option_details))

            # 6. Liquidity check (Warning only)
            results.append(self._check_liquidity(symbol))

        # Option-specific checks
        if contract_type == "OPT":
            results.extend(
                self._check_option_risks(
                    symbol, action, quantity, option_details, account_summary, current_positions
                )
            )

        # Drawdown check for existing positions
        if action == "SELL":
            results.append(
                self._check_max_drawdown(symbol, price, current_positions)
            )

        return results

    def has_blocking_issues(self, results: List[RiskCheckResult]) -> bool:
        """Check if any risk check blocked the operation.

        Args:
            results: List of risk check results

        Returns:
            True if any check has BLOCK level
        """
        return any(r.level == RiskLevel.BLOCK for r in results)

    def get_warnings(self, results: List[RiskCheckResult]) -> List[RiskCheckResult]:
        """Get all warning-level results.

        Args:
            results: List of risk check results

        Returns:
            List of warnings
        """
        return [r for r in results if r.level == RiskLevel.WARNING]

    # ==================== Individual Risk Checks ====================

    def _check_stop_loss(self, action: str, stop_loss: Optional[float]) -> RiskCheckResult:
        """Check if stop loss is required and present.

        Munger principle: First rule - don't lose money. Second rule - don't forget rule #1.
        """
        if not self.config.risk_require_stop_loss:
            return RiskCheckResult(
                "stop_loss_check",
                RiskLevel.PASS,
                "Stop loss not required by configuration",
            )

        if action == "BUY" and not stop_loss:
            return RiskCheckResult(
                "stop_loss_check",
                RiskLevel.BLOCK,
                "Stop loss is required for all BUY orders",
                {"required": True, "provided": False},
            )

        return RiskCheckResult(
            "stop_loss_check",
            RiskLevel.PASS,
            f"Stop loss check passed: {stop_loss}" if stop_loss else "SELL order (no stop loss required)",
        )

    def _check_margin_usage(self, account_summary: Dict[str, Any]) -> RiskCheckResult:
        """Check if margin trading is being used.

        Munger principle: Avoid leverage - it can destroy you.
        """
        if not self.config.risk_allow_margin:
            # Check if account has margin loan
            excess_liquidity = float(
                account_summary.get("ExcessLiquidity", {}).get("value", 0)
            )
            net_liquidation = float(
                account_summary.get("NetLiquidation", {}).get("value", 1)
            )

            # If excess liquidity is significantly less than net liquidation, margin might be in use
            if excess_liquidity < net_liquidation * 0.5:
                return RiskCheckResult(
                    "margin_check",
                    RiskLevel.BLOCK,
                    "Margin trading is not allowed",
                    {
                        "excess_liquidity": excess_liquidity,
                        "net_liquidation": net_liquidation,
                    },
                )

        return RiskCheckResult(
            "margin_check",
            RiskLevel.PASS,
            "No margin usage detected",
        )

    def _check_position_size(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: Optional[float],
        account_summary: Dict[str, Any],
        current_positions: List[Any],
    ) -> RiskCheckResult:
        """Check single position concentration.

        Munger principle: Wide diversification is only required when investors do not know what they are doing.
        But even concentrated positions should have limits.
        """
        net_liquidation = float(
            account_summary.get("NetLiquidation", {}).get("value", 0)
        )

        if net_liquidation == 0:
            return RiskCheckResult(
                "position_size_check",
                RiskLevel.BLOCK,
                "Cannot determine account value",
            )

        # Calculate current position value for this symbol
        current_value = 0
        for pos in current_positions:
            if hasattr(pos, 'contract') and pos.contract.symbol == symbol:
                current_value = pos.position * pos.avgCost

        # Calculate new position value
        order_value = quantity * (price or 0) if price else 0
        if action == "BUY":
            new_value = abs(current_value) + order_value
        else:  # SELL
            new_value = abs(current_value) - order_value

        position_pct = (new_value / net_liquidation) * 100

        if position_pct > self.config.risk_max_single_position_pct:
            return RiskCheckResult(
                "position_size_check",
                RiskLevel.BLOCK,
                f"Position would exceed limit: {position_pct:.1f}% > {self.config.risk_max_single_position_pct}%",
                {
                    "symbol": symbol,
                    "new_position_pct": position_pct,
                    "limit_pct": self.config.risk_max_single_position_pct,
                    "new_value": new_value,
                    "net_liquidation": net_liquidation,
                },
            )

        return RiskCheckResult(
            "position_size_check",
            RiskLevel.PASS,
            f"Position size OK: {position_pct:.1f}% of portfolio",
            {"position_pct": position_pct},
        )

    def _check_total_position_limit(
        self,
        action: str,
        quantity: int,
        price: Optional[float],
        account_summary: Dict[str, Any],
        current_positions: List[Any],
    ) -> RiskCheckResult:
        """Check total portfolio exposure.

        Munger principle: Always leave room for error and uncertainty.
        """
        net_liquidation = float(
            account_summary.get("NetLiquidation", {}).get("value", 0)
        )

        # Calculate current total position value
        total_position_value = sum(
            abs(pos.position * pos.avgCost) for pos in current_positions
        )

        # Add new order value if buying
        if action == "BUY" and price:
            total_position_value += quantity * price

        total_position_pct = (total_position_value / net_liquidation) * 100

        if total_position_pct > self.config.risk_max_total_position_pct:
            return RiskCheckResult(
                "total_position_check",
                RiskLevel.BLOCK,
                f"Total position would exceed limit: {total_position_pct:.1f}% > {self.config.risk_max_total_position_pct}%",
                {
                    "total_position_pct": total_position_pct,
                    "limit_pct": self.config.risk_max_total_position_pct,
                },
            )

        return RiskCheckResult(
            "total_position_check",
            RiskLevel.PASS,
            f"Total position OK: {total_position_pct:.1f}% invested",
            {"total_position_pct": total_position_pct},
        )

    def _check_max_drawdown(
        self, symbol: str, current_price: Optional[float], current_positions: List[Any]
    ) -> RiskCheckResult:
        """Check if position has exceeded maximum drawdown.

        Munger principle: The first rule of compounding - never interrupt it unnecessarily.
        But cut losses when they exceed acceptable limits.
        """
        if not current_price:
            return RiskCheckResult(
                "drawdown_check",
                RiskLevel.PASS,
                "No price provided for drawdown check",
            )

        for pos in current_positions:
            if hasattr(pos, 'contract') and pos.contract.symbol == symbol:
                avg_cost = pos.avgCost
                drawdown_pct = ((current_price - avg_cost) / avg_cost) * 100

                if drawdown_pct < -self.config.risk_max_drawdown_pct:
                    return RiskCheckResult(
                        "drawdown_check",
                        RiskLevel.WARNING,
                        f"Position exceeds max drawdown: {drawdown_pct:.1f}% < -{self.config.risk_max_drawdown_pct}%",
                        {
                            "symbol": symbol,
                            "drawdown_pct": drawdown_pct,
                            "avg_cost": avg_cost,
                            "current_price": current_price,
                        },
                    )

        return RiskCheckResult(
            "drawdown_check",
            RiskLevel.PASS,
            "Drawdown within acceptable limits",
        )

    def _check_volatility(
        self, symbol: str, option_details: Optional[Dict[str, Any]]
    ) -> RiskCheckResult:
        """Check for high volatility (warning only).

        Munger principle: Avoid dealing with people of questionable character.
        In markets: Avoid highly volatile, speculative instruments.
        """
        if option_details and "implied_volatility" in option_details:
            iv = option_details["implied_volatility"]
            if iv > self.config.risk_high_volatility_threshold:
                return RiskCheckResult(
                    "volatility_check",
                    RiskLevel.WARNING,
                    f"High implied volatility detected: {iv:.1f}% > {self.config.risk_high_volatility_threshold}%",
                    {"implied_volatility": iv},
                )

        return RiskCheckResult(
            "volatility_check",
            RiskLevel.PASS,
            "Volatility check passed",
        )

    def _check_liquidity(self, symbol: str) -> RiskCheckResult:
        """Check liquidity (warning only).

        Munger principle: Only invest in what you understand and can easily exit.
        """
        # This would require real-time volume data
        # For now, return a pass - implement with actual volume data
        return RiskCheckResult(
            "liquidity_check",
            RiskLevel.PASS,
            "Liquidity check passed (requires implementation with volume data)",
        )

    def _check_option_risks(
        self,
        symbol: str,
        action: str,
        quantity: int,
        option_details: Optional[Dict[str, Any]],
        account_summary: Dict[str, Any],
        current_positions: List[Any],
    ) -> List[RiskCheckResult]:
        """Check option-specific risks.

        Munger principle: Avoid unnecessary complexity and risk.
        """
        results = []

        if not option_details:
            return [
                RiskCheckResult(
                    "option_details_check",
                    RiskLevel.BLOCK,
                    "Option details required for option trading",
                )
            ]

        option_type = option_details.get("option_type", "")
        right = option_details.get("right", "")
        strike = option_details.get("strike", 0)

        # 1. Check option position limit
        net_liquidation = float(
            account_summary.get("NetLiquidation", {}).get("value", 0)
        )

        # Calculate current option value
        current_option_value = sum(
            abs(pos.position * pos.avgCost)
            for pos in current_positions
            if hasattr(pos, 'contract') and pos.contract.secType == "OPT"
        )

        # Add new option value
        option_price = option_details.get("price", 0)
        new_option_value = current_option_value + (quantity * option_price * 100)  # 100 shares per contract

        option_pct = (new_option_value / net_liquidation) * 100

        if option_pct > self.config.risk_max_option_position_pct:
            results.append(
                RiskCheckResult(
                    "option_position_limit",
                    RiskLevel.BLOCK,
                    f"Option position would exceed limit: {option_pct:.1f}% > {self.config.risk_max_option_position_pct}%",
                    {"option_pct": option_pct},
                )
            )
        else:
            results.append(
                RiskCheckResult(
                    "option_position_limit",
                    RiskLevel.PASS,
                    f"Option position OK: {option_pct:.1f}%",
                )
            )

        # 2. Check naked option selling
        if action == "SELL":
            if right == "C":  # Selling calls
                # Check if covered call (must own underlying)
                has_underlying = any(
                    pos.contract.symbol == symbol and pos.contract.secType == "STK" and pos.position >= quantity * 100
                    for pos in current_positions
                )

                if not has_underlying:
                    results.append(
                        RiskCheckResult(
                            "naked_call_check",
                            RiskLevel.BLOCK,
                            "Naked call selling is prohibited. Must own underlying shares for covered call.",
                            {"required_shares": quantity * 100},
                        )
                    )
                else:
                    results.append(
                        RiskCheckResult(
                            "covered_call_check",
                            RiskLevel.PASS,
                            f"Covered call: sufficient underlying shares owned",
                        )
                    )

            elif right == "P":  # Selling puts
                # Check cash collateral for naked puts (100% cash or 95% bonds)
                cash_balance = float(
                    account_summary.get("CashBalance", {}).get("value", 0)
                )

                # Calculate bond value (SGOV, etc.) - simplified for now
                bond_value = sum(
                    abs(pos.position * pos.avgCost)
                    for pos in current_positions
                    if hasattr(pos, 'contract') and pos.contract.symbol in ["SGOV", "BIL", "SHV"]
                )

                available_collateral = cash_balance + (bond_value * self.config.risk_bond_collateral_multiplier)
                required_collateral = quantity * strike * 100

                if available_collateral < required_collateral:
                    results.append(
                        RiskCheckResult(
                            "naked_put_collateral",
                            RiskLevel.BLOCK,
                            f"Insufficient collateral for naked put: ${available_collateral:.2f} < ${required_collateral:.2f}",
                            {
                                "available": available_collateral,
                                "required": required_collateral,
                                "cash": cash_balance,
                                "bond_value": bond_value,
                            },
                        )
                    )
                else:
                    results.append(
                        RiskCheckResult(
                            "naked_put_collateral",
                            RiskLevel.PASS,
                            f"Sufficient collateral for naked put: ${available_collateral:.2f}",
                        )
                    )

        return results


# Global risk manager instance
_risk_manager: Optional[RiskManager] = None


def get_risk_manager() -> RiskManager:
    """Get or create the global risk manager instance."""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager
