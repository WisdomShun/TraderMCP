"""
Fundamental data tools
"""
from typing import Dict, Any, Optional
from src.ib_client import get_ib_client
from src.logger import logger

ib_client = get_ib_client()


async def get_fundamental_data(
    symbol: str,
    data_type: str = "ReportsFinSummary"
) -> Dict[str, Any]:
    """
    获取标的基本面数据
    
    Args:
        symbol: 股票代码
        data_type: 数据类型
            - CompanyOverview: 公司概况
            - FinancialStatements: 财务报表
            - ReportsFinSummary: 财务摘要（推荐）
            - ReportSnapshot: 分析师报告快照
            - RESC: 研究报告
            
    Returns:
        基本面数据字典
    """
    try:
        logger.info(f"Fetching fundamental data for {symbol} (type={data_type})...")
        
        await ib_client.ensure_connected()
        
        contract = ib_client.create_stock_contract(symbol)
        
        # Request fundamental data
        # Note: This requires IB fundamental data subscription
        fund_data = await ib_client.ib.reqFundamentalDataAsync(contract, data_type)
        
        if not fund_data:
            logger.warning(f"No fundamental data returned for {symbol}")
            return {
                'symbol': symbol,
                'data_type': data_type,
                'error': 'No data available (may require subscription)'
            }
        
        # Parse XML data (IB returns XML format)
        # For now, return raw data - can add XML parsing later
        logger.info(f"Retrieved fundamental data for {symbol}")
        return {
            'symbol': symbol,
            'data_type': data_type,
            'data': fund_data,
            'note': 'Data is in XML format - consider parsing for specific fields'
        }
        
    except Exception as e:
        logger.error(f"Error getting fundamental data: {e}")
        return {
            'symbol': symbol,
            'error': str(e),
            'note': 'Fundamental data may require IB subscription'
        }


async def get_company_overview(symbol: str) -> Dict[str, Any]:
    """
    获取公司概况信息
    
    Args:
        symbol: 股票代码
        
    Returns:
        公司概况数据
    """
    return await get_fundamental_data(symbol, data_type="CompanyOverview")


async def get_financial_summary(symbol: str) -> Dict[str, Any]:
    """
    获取财务摘要
    
    Args:
        symbol: 股票代码
        
    Returns:
        财务摘要数据
    """
    return await get_fundamental_data(symbol, data_type="ReportsFinSummary")


async def get_analyst_reports(symbol: str) -> Dict[str, Any]:
    """
    获取分析师报告
    
    Args:
        symbol: 股票代码
        
    Returns:
        分析师报告数据
    """
    return await get_fundamental_data(symbol, data_type="ReportSnapshot")


async def get_contract_details(symbol: str) -> Dict[str, Any]:
    """
    获取合约详细信息（不需要订阅）
    
    Args:
        symbol: 股票代码
        
    Returns:
        合约详细信息，包含行业、公司名称等
    """
    try:
        logger.info(f"Fetching contract details for {symbol}...")
        
        await ib_client.ensure_connected()
        
        contract = ib_client.create_stock_contract(symbol)
        
        # Request contract details
        details = await ib_client.ib.reqContractDetailsAsync(contract)
        
        if not details:
            logger.warning(f"No contract details found for {symbol}")
            return {'symbol': symbol, 'error': 'No contract details found'}
        
        # Extract relevant information
        detail = details[0]
        contract_desc = detail.contract
        
        result = {
            'symbol': contract_desc.symbol,
            'company_name': detail.longName,
            'industry': detail.industry,
            'category': detail.category,
            'subcategory': detail.subcategory,
            'exchange': contract_desc.primaryExchange,
            'currency': contract_desc.currency,
            'contract_id': contract_desc.conId,
            'trading_class': contract_desc.tradingClass,
        }
        
        logger.info(f"Retrieved contract details for {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting contract details: {e}")
        return {'symbol': symbol, 'error': str(e)}


async def get_company_info(symbol: str) -> Dict[str, Any]:
    """
    获取公司基本信息（推荐使用，不需要额外订阅）
    
    Args:
        symbol: 股票代码
        
    Returns:
        公司基本信息
    """
    return await get_contract_details(symbol)
