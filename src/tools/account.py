"""
Account management tools
"""
from typing import Dict, Any, Optional
from src.ib_client import get_ib_client
from src.logger import logger

ib_client = get_ib_client()


async def get_account_summary() -> Dict[str, Any]:
    """
    获取账户摘要信息
    
    Returns:
        账户信息字典，包含：
        - NetLiquidation: 净资产
        - TotalCashValue: 现金总额
        - AvailableFunds: 可用资金
        - BuyingPower: 购买力
        - GrossPositionValue: 总持仓价值
        - MaintMarginReq: 维持保证金
        等其他账户指标
    """
    try:
        logger.info("Fetching account summary...")
        summary = await ib_client.get_account_summary()
        
        # Parse and format the data
        result = {
            'account': summary.get('account', 'N/A'),
            'net_liquidation': float(summary.get('NetLiquidation', 0)),
            'total_cash': float(summary.get('TotalCashValue', 0)),
            'available_funds': float(summary.get('AvailableFunds', 0)),
            'buying_power': float(summary.get('BuyingPower', 0)),
            'gross_position_value': float(summary.get('GrossPositionValue', 0)),
            'maint_margin_req': float(summary.get('MaintMarginReq', 0)),
            'excess_liquidity': float(summary.get('ExcessLiquidity', 0)),
            'currency': summary.get('Currency', 'USD'),
        }
        
        logger.info(f"Account summary retrieved: Net Liquidation = ${result['net_liquidation']:,.2f}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting account summary: {e}")
        return {
            'error': str(e),
            'account': 'N/A',
            'net_liquidation': 0,
            'total_cash': 0
        }


async def get_cash_balance() -> Dict[str, Any]:
    """
    获取现金余额详情
    
    Returns:
        现金信息字典
    """
    try:
        summary = await ib_client.get_account_summary()
        
        result = {
            'total_cash': float(summary.get('TotalCashValue', 0)),
            'settled_cash': float(summary.get('SettledCash', 0)),
            'cash_balance': float(summary.get('CashBalance', 0)),
            'currency': summary.get('Currency', 'USD'),
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting cash balance: {e}")
        return {'error': str(e), 'total_cash': 0}


async def get_margin_info() -> Dict[str, Any]:
    """
    获取保证金信息
    
    Returns:
        保证金信息字典
    """
    try:
        summary = await ib_client.get_account_summary()
        
        result = {
            'available_funds': float(summary.get('AvailableFunds', 0)),
            'excess_liquidity': float(summary.get('ExcessLiquidity', 0)),
            'buying_power': float(summary.get('BuyingPower', 0)),
            'maint_margin_req': float(summary.get('MaintMarginReq', 0)),
            'init_margin_req': float(summary.get('InitMarginReq', 0)),
            'leverage': float(summary.get('Leverage-S', 0)),
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting margin info: {e}")
        return {'error': str(e)}
