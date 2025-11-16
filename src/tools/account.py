"""
Account management tools
"""
from typing import Dict
from src.ib_client import get_ib_client
from src.logger import logger
from src.models import AccountSummary

ib_client = get_ib_client()


def _parse_account_values_to_dict(account_values, currency: str = "USD") -> Dict[str, str]:
    """
    将 IB AccountValue 列表转换为字典
    
    Args:
        account_values: IB AccountValue 对象列表
        currency: 筛选的币种
        
    Returns:
        字段名到值的映射字典
    """
    data = {}
    for av in account_values:
        # 跳过不匹配的币种（除非是 BASE 币种）
        if av.currency != currency:
            continue
        data[av.tag] = av.value
    return data


async def get_account_summary(currency: str = "USD") -> AccountSummary:
    """
    获取账户摘要信息（返回完整的账户数据模型）
    
    Args:
        currency: 币种过滤（默认 USD）
    
    Returns:
        AccountSummary 对象，包含净资产、现金、持仓市值等完整信息
    """
    try:
        logger.info(f"Fetching account summary for currency: {currency}...")
        account_values = await ib_client.get_account_summary()
        
        # 转换为字典方便访问
        data = _parse_account_values_to_dict(account_values, currency)
        
        # 获取账户名称
        account_name = "Unknown"
        if account_values:
            account_name = account_values[0].account
        
        # 构建 AccountSummary 对象
        summary = AccountSummary(
            # 基本信息
            account_or_group=data.get('AccountOrGroup', account_name),
            currency=data.get('Currency', currency),
            real_currency=data.get('RealCurrency', currency),
            exchange_rate=float(data.get('ExchangeRate', 1.0)),
            
            # 现金
            cash_balance=float(data.get('CashBalance', 0)),
            total_cash_balance=float(data.get('TotalCashBalance', 0)),
            accrued_cash=float(data.get('AccruedCash', 0)),
            fx_cash_balance=float(data.get('FxCashBalance', 0)),
            
            # 持仓市值
            stock_market_value=float(data.get('StockMarketValue', 0)),
            option_market_value=float(data.get('OptionMarketValue', 0)),
            future_option_value=float(data.get('FutureOptionValue', 0)),
            warrant_value=float(data.get('WarrantValue', 0)),
            issuer_option_value=float(data.get('IssuerOptionValue', 0)),
            
            # 基金和债券
            fund_value=float(data.get('FundValue', 0)),
            mutual_fund_value=float(data.get('MutualFundValue', 0)),
            money_market_fund_value=float(data.get('MoneyMarketFundValue', 0)),
            corporate_bond_value=float(data.get('CorporateBondValue', 0)),
            t_bond_value=float(data.get('TBondValue', 0)),
            t_bill_value=float(data.get('TBillValue', 0)),
            
            # 净值和盈亏
            net_liquidation=float(data.get('NetLiquidationByCurrency', 0)),
            unrealized_pnl=float(data.get('UnrealizedPnL', 0)),
            realized_pnl=float(data.get('RealizedPnL', 0)),
            futures_pnl=float(data.get('FuturesPNL', 0)),
            net_dividend=float(data.get('NetDividend', 0)),
        )
        
        logger.info(f"Account summary retrieved for {summary.account_or_group}")
        logger.info(f"  Net Liquidation: ${summary.net_liquidation:,.2f}")
        logger.info(f"  Cash: ${summary.total_cash_balance:,.2f} ({summary.cash_percentage:.1f}%)")
        logger.info(f"  Invested: ${summary.total_market_value:,.2f} ({summary.invested_percentage:.1f}%)")
        logger.info(f"  Unrealized P&L: ${summary.unrealized_pnl:,.2f}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting account summary: {e}", exc_info=True)
        # 返回空的摘要对象
        return AccountSummary(
            account_or_group="Error",
            currency=currency,
            real_currency=currency,
        )