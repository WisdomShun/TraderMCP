"""
Position management tools
"""
from typing import List, Optional
from ib_insync import Position, PortfolioItem
from src.ib_client import get_ib_client
from src.logger import logger
from src.models import PositionSummary, StockInfo, PositionStock, OptionInfo, PositionOption

ib_client = get_ib_client()


async def _get_positions(asset_type: Optional[str] = "ALL") -> List[PortfolioItem]:
    """
    获取仓位信息（返回原生 ib_insync PortfolioItem 对象，包含市值和盈亏）
    
    Args:
        asset_type: 资产类型过滤 (STK=股票, OPT=期权, ALL=所有)
        
    Returns:
        PortfolioItem 对象列表，包含 contract, position, marketPrice, marketValue,
        averageCost, unrealizedPNL, realizedPNL 等属性
    """
    try:
        logger.info(f"Fetching positions (asset_type={asset_type})...")
        
        # Get portfolio items (includes market value and P&L)
        positions = await ib_client.get_portfolio()
        
        # Filter by asset type if needed
        if asset_type != "ALL":
            positions = [p for p in positions if p.contract.secType == asset_type]

        logger.info(f"Retrieved {len(positions)} positions")
        return positions

    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return []


async def get_stock_positions() -> List[PositionStock]:
    """
    获取股票仓位（返回原生 PortfolioItem 对象）
    
    Returns:
        股票 PortfolioItem 列表
    """
    ibkr_stock_positions = await _get_positions(asset_type="STK")

    return [
        PositionStock(
            detail=StockInfo(
                symbol=p.contract.localSymbol,
                exchange=p.contract.exchange,
                currency=p.contract.currency
            ),
            position=p.position,
            market_price=p.marketPrice,
            market_value=p.marketValue,
            average_cost=p.averageCost,
            unrealized_pnl=p.unrealizedPNL,
            realized_pnl=p.realizedPNL
        ) for p in ibkr_stock_positions
    ]


async def get_option_positions() -> List[PositionOption]:
    """
    获取期权仓位（返回原生 PortfolioItem 对象）
    
    Returns:
        期权 PortfolioItem 列表
    """
    ibkr_option_positions = await _get_positions(asset_type="OPT")

    return [
        PositionOption(
            detail=OptionInfo(
                symbol=p.contract.symbol,
                exchange=p.contract.primaryExchange,
                right=p.contract.right,
                strike=p.contract.strike,
                expiry=p.contract.expiry
            ),
            position=p.position,
            market_price=p.marketPrice,
            market_value=p.marketValue,
            average_cost=p.averageCost,
            unrealized_pnl=p.unrealizedPNL,
            realized_pnl=p.realizedPNL
        ) for p in ibkr_option_positions
    ]


async def get_position_summary() -> PositionSummary:
    """
    获取仓位汇总信息（返回计算后的 Pydantic Model）
    
    Returns:
        PositionSummary 对象，包含总市值、总盈亏、仓位占比等计算指标
    """

    try:
        stock_positions = await get_stock_positions()
        option_positions = await get_option_positions()

        # stock_market_value = sum(p.market_value for p in stock_positions)
        # option_market_value = sum(p.market_value for p in option_positions)

        # total_unrealized_pnl = sum(p.unrealized_pnl for p in stock_positions) + sum(p.unrealized_pnl for p in option_positions)
        # total_realized_pnl = sum(p.realized_pnl for p in stock_positions) + sum(p.realized_pnl for p in option_positions)

        return PositionSummary(
            stock_positions=stock_positions,
            option_positions=option_positions,
            # total_market_value=stock_market_value + option_market_value,
            # stock_market_value=stock_market_value,
            # option_market_value=option_market_value,
            # total_unrealized_pnl=total_unrealized_pnl,
            # total_realized_pnl=total_realized_pnl,
        )
        
    except Exception as e:
        logger.error(f"Error getting position summary: {e}")
        return PositionSummary(
            stock_positions=[],
            option_positions=[],
            total_market_value=0.0,
            stock_market_value=0.0,
            option_market_value=0.0,
            total_unrealized_pnl=0.0,
            total_realized_pnl=0.0,
        )
