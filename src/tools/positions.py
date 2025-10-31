"""
Position management tools
"""
from typing import List, Dict, Any, Optional
from src.ib_client import get_ib_client
from src.logger import logger

ib_client = get_ib_client()


async def get_positions(asset_type: Optional[str] = "ALL") -> List[Dict[str, Any]]:
    """
    获取仓位信息
    
    Args:
        asset_type: 资产类型过滤 (STK=股票, OPT=期权, ALL=所有)
        
    Returns:
        仓位列表，包含标的、数量、成本价等信息
    """
    try:
        logger.info(f"Fetching positions (asset_type={asset_type})...")
        
        # Get portfolio items (includes market value)
        portfolio = await ib_client.get_portfolio()
        
        result = []
        for item in portfolio:
            # Filter by asset type
            if asset_type != "ALL" and item['sec_type'] != asset_type:
                continue
            
            position_data = {
                'symbol': item['symbol'],
                'asset_type': item['sec_type'],
                'position': item['position'],
                'market_price': item['market_price'],
                'market_value': item['market_value'],
                'average_cost': item['avg_cost'],
                'unrealized_pnl': item['unrealized_pnl'],
                'realized_pnl': item['realized_pnl'],
                'unrealized_pnl_pct': (item['unrealized_pnl'] / (abs(item['position']) * item['avg_cost']) * 100) 
                                      if item['position'] != 0 and item['avg_cost'] != 0 else 0,
            }
            
            # Add option-specific details
            if item['sec_type'] == 'OPT':
                contract = item['contract']
                position_data['expiration'] = getattr(contract, 'lastTradeDateOrContractMonth', 'N/A')
                position_data['strike'] = getattr(contract, 'strike', 0)
                position_data['right'] = getattr(contract, 'right', 'N/A')  # C or P
            
            result.append(position_data)
        
        logger.info(f"Retrieved {len(result)} positions")
        return result
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return [{'error': str(e)}]


async def get_stock_positions() -> List[Dict[str, Any]]:
    """
    获取股票仓位
    
    Returns:
        股票仓位列表
    """
    return await get_positions(asset_type="STK")


async def get_option_positions() -> List[Dict[str, Any]]:
    """
    获取期权仓位
    
    Returns:
        期权仓位列表
    """
    return await get_positions(asset_type="OPT")


async def get_position_summary() -> Dict[str, Any]:
    """
    获取仓位汇总信息
    
    Returns:
        仓位汇总字典，包含总市值、总盈亏等
    """
    try:
        portfolio = await ib_client.get_portfolio()
        account = await ib_client.get_account_summary()
        
        total_market_value = sum(item['market_value'] for item in portfolio)
        total_unrealized_pnl = sum(item['unrealized_pnl'] for item in portfolio)
        total_realized_pnl = sum(item['realized_pnl'] for item in portfolio)
        
        stock_value = sum(item['market_value'] for item in portfolio if item['sec_type'] == 'STK')
        option_value = sum(item['market_value'] for item in portfolio if item['sec_type'] == 'OPT')
        
        net_liquidation = float(account.get('NetLiquidation', 0))
        
        result = {
            'total_positions': len(portfolio),
            'stock_positions': len([p for p in portfolio if p['sec_type'] == 'STK']),
            'option_positions': len([p for p in portfolio if p['sec_type'] == 'OPT']),
            'total_market_value': total_market_value,
            'stock_market_value': stock_value,
            'option_market_value': option_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': total_realized_pnl,
            'net_liquidation': net_liquidation,
            'position_pct': (total_market_value / net_liquidation * 100) if net_liquidation > 0 else 0,
            'stock_pct': (stock_value / net_liquidation * 100) if net_liquidation > 0 else 0,
            'option_pct': (option_value / net_liquidation * 100) if net_liquidation > 0 else 0,
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting position summary: {e}")
        return {'error': str(e)}
