"""
Market data tools for historical K-line data with caching
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.ib_client import get_ib_client
from src.cache.db_manager import DatabaseManager
from src.logger import logger

ib_client = get_ib_client()
db = DatabaseManager()


# Bar size mapping
BAR_SIZE_MAP = {
    '1D': '1 day',
    '1W': '1 week',
    '1M': '1 month',
    '1H': '1 hour',
    '30min': '30 mins',
    '15min': '15 mins',
    '5min': '5 mins',
    '1min': '1 min',
}


async def get_historical_kline(
    symbol: str,
    bar_size: str = '1D',
    duration: str = '1 Y',
    end_datetime: Optional[str] = None,
    use_cache: bool = True,
    force_refresh: bool = False
) -> List[Dict[str, Any]]:
    """
    获取历史K线数据（带缓存）
    
    Args:
        symbol: 股票代码
        bar_size: K线类型 (1D=日K, 1W=周K, 1M=月K等)
        duration: 时间范围 (如 "1 Y", "6 M", "1 W")
        end_datetime: 结束时间（可选，默认当前时间）
        use_cache: 是否使用缓存（默认True）
        force_refresh: 是否强制刷新（忽略缓存）
        
    Returns:
        K线数据列表，每项包含 datetime, open, high, low, close, volume
    """
    try:
        logger.info(f"Fetching kline data for {symbol} ({bar_size}, {duration})...")
        
        # Map bar size to IB format
        ib_bar_size = BAR_SIZE_MAP.get(bar_size, bar_size)
        
        # Check cache first (if not forcing refresh)
        if use_cache and not force_refresh:
            cached_data = db.get_kline_data(symbol, bar_size)
            
            if cached_data:
                logger.info(f"Found {len(cached_data)} cached bars for {symbol}")
                
                # Check if we need to update with recent data
                latest_cached = db.get_latest_kline_datetime(symbol, bar_size)
                
                if latest_cached:
                    latest_dt = datetime.fromisoformat(latest_cached)
                    now = datetime.now()
                    
                    # If latest cache is recent (within 1 day), return cached data
                    if (now - latest_dt).days < 1:
                        logger.info(f"Cache is up-to-date, returning {len(cached_data)} bars")
                        return cached_data
                    
                    # Otherwise, fetch incremental data
                    logger.info("Fetching incremental data since last cache...")
                    contract = ib_client.create_stock_contract(symbol)
                    
                    # Calculate duration from latest cache to now
                    days_diff = (now - latest_dt).days + 1
                    inc_duration = f"{days_diff} D"
                    
                    new_data = await ib_client.get_historical_data(
                        contract,
                        duration=inc_duration,
                        bar_size=ib_bar_size,
                        what_to_show='TRADES',
                        use_rth=True
                    )
                    
                    if new_data:
                        # Save new data to cache
                        db.save_kline_data(symbol, bar_size, new_data)
                        
                        # Merge with cached data (remove duplicates)
                        existing_dates = {item['datetime'] for item in cached_data}
                        for bar in new_data:
                            if bar['datetime'] not in existing_dates:
                                cached_data.append(bar)
                        
                        # Sort by datetime
                        cached_data.sort(key=lambda x: x['datetime'])
                        
                        logger.info(f"Updated cache with {len(new_data)} new bars")
                    
                    return cached_data
        
        # Fetch full historical data from IB
        logger.info(f"Fetching full historical data from IB...")
        contract = ib_client.create_stock_contract(symbol)
        
        data = await ib_client.get_historical_data(
            contract,
            duration=duration,
            bar_size=ib_bar_size,
            what_to_show='TRADES',
            use_rth=True,
            end_datetime=end_datetime or ''
        )
        
        if not data:
            logger.warning(f"No data returned for {symbol}")
            return []
        
        # Save to cache
        if use_cache:
            db.save_kline_data(symbol, bar_size, data)
            logger.info(f"Cached {len(data)} bars for {symbol}")
        
        return data
        
    except Exception as e:
        logger.error(f"Error getting kline data: {e}")
        return [{'error': str(e)}]


async def get_daily_kline(symbol: str, days: int = 365) -> List[Dict[str, Any]]:
    """
    获取日K线数据
    
    Args:
        symbol: 股票代码
        days: 天数（默认365天）
        
    Returns:
        日K线数据列表
    """
    duration = f"{days} D"
    return await get_historical_kline(symbol, bar_size='1D', duration=duration)


async def get_weekly_kline(symbol: str, weeks: int = 52) -> List[Dict[str, Any]]:
    """
    获取周K线数据
    
    Args:
        symbol: 股票代码
        weeks: 周数（默认52周）
        
    Returns:
        周K线数据列表
    """
    duration = f"{weeks} W"
    return await get_historical_kline(symbol, bar_size='1W', duration=duration)


async def get_monthly_kline(symbol: str, months: int = 12) -> List[Dict[str, Any]]:
    """
    获取月K线数据
    
    Args:
        symbol: 股票代码
        months: 月数（默认12个月）
        
    Returns:
        月K线数据列表
    """
    # IB uses 'Y' for year, so convert months to years
    if months <= 12:
        duration = "1 Y"
    else:
        years = months // 12
        duration = f"{years} Y"
    
    return await get_historical_kline(symbol, bar_size='1M', duration=duration)


async def clear_kline_cache(symbol: Optional[str] = None, bar_size: Optional[str] = None):
    """
    清除K线缓存
    
    Args:
        symbol: 股票代码（可选，不提供则清除所有）
        bar_size: K线类型（可选）
    """
    try:
        # This would require adding a clear method to DatabaseManager
        logger.warning("Cache clearing not yet implemented")
        pass
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
