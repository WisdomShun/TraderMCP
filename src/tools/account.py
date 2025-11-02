"""
Account management tools
"""
from src.ib_client import get_ib_client
from src.logger import logger
from src.models import AccountSummary

ib_client = get_ib_client()

async def get_account_summary() -> AccountSummary:
    """
    获取账户摘要信息（返回计算后的 Pydantic Model）
    
    Returns:
        AccountSummary 对象，包含净资产、现金、可用资金、购买力等关键指标
    """
    try:
        logger.info("Fetching account summary...")
        account_values = await ib_client.get_account_summary()
        
        # Parse AccountValue list into dict
        data = {}
        account_name = "N/A"
        for av in account_values:
            data[av.tag] = av.value
            if account_name == "N/A":
                account_name = av.account
        
        # Build summary model
        summary = AccountSummary(
            account=account_name,
            net_liquidation=float(data.get('NetLiquidation', 0)),
            gross_position_value=float(data.get('GrossPositionValue', 0)),
            currency=data.get('Currency', 'USD'),

            available_funds=float(data.get('AvailableFunds', 0)),
            buying_power=float(data.get('BuyingPower', 0)),
            maint_margin_req=float(data.get('MaintMarginReq', 0)),
            excess_liquidity=float(data.get('ExcessLiquidity', 0)),
            init_margin_req=float(data.get('InitMarginReq', 0)),
            leverage=float(data.get('Leverage-S', 0)),

            total_cash=float(data.get('TotalCashValue', 0)),
            settled_cash=float(data.get('SettledCash', 0)),
            cash_balance=float(data.get('CashBalance', 0)),
        )
        
        logger.info(f"Account summary retrieved: Net Liquidation = ${summary.net_liquidation:,.2f}")
        return summary
        
    except Exception as e:
        logger.error(f"Error getting account summary: {e}")
        # Return empty summary on error
        return AccountSummary(
            account="N/A",
            net_liquidation=0.0,
            gross_position_value=0.0,
            available_funds=0.0,
            buying_power=0.0,
            maint_margin_req=0.0,
            excess_liquidity=0.0,
            init_margin_req=0.0,
            leverage=0.0,
            total_cash=0.0,
            settled_cash=0.0,
            cash_balance=0.0,
            currency="USD",
        )