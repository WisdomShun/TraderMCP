"""
Trading calendar tools
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
import pandas_market_calendars as mcal
from src.logger import logger


def get_trading_calendar(
    start_date: str,
    end_date: str,
    exchange: str = "NYSE"
) -> List[Dict[str, Any]]:
    """
    获取交易日历
    
    Args:
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        exchange: 交易所代码（默认NYSE，可选NASDAQ, CME等）
        
    Returns:
        交易日列表，包含日期、是否交易日、开盘收盘时间等
    """
    try:
        logger.info(f"Fetching trading calendar for {exchange} from {start_date} to {end_date}...")
        
        # Get the calendar
        calendar = mcal.get_calendar(exchange)
        
        # Get schedule
        schedule = calendar.schedule(start_date=start_date, end_date=end_date)
        
        # Convert to list of dicts
        result = []
        for date, row in schedule.iterrows():
            result.append({
                'date': date.strftime('%Y-%m-%d'),
                'is_trading_day': True,
                'market_open': row['market_open'].strftime('%Y-%m-%d %H:%M:%S%z'),
                'market_close': row['market_close'].strftime('%Y-%m-%d %H:%M:%S%z'),
                'exchange': exchange
            })
        
        logger.info(f"Retrieved {len(result)} trading days")
        return result
        
    except Exception as e:
        logger.error(f"Error getting trading calendar: {e}")
        return [{'error': str(e)}]


def is_trading_day(date: str, exchange: str = "NYSE") -> Dict[str, Any]:
    """
    检查指定日期是否为交易日
    
    Args:
        date: 日期（YYYY-MM-DD）
        exchange: 交易所代码
        
    Returns:
        包含是否交易日和开盘收盘时间的字典
    """
    try:
        calendar = mcal.get_calendar(exchange)
        
        # Check if it's a trading day
        schedule = calendar.schedule(start_date=date, end_date=date)
        
        if schedule.empty:
            return {
                'date': date,
                'is_trading_day': False,
                'exchange': exchange
            }
        
        row = schedule.iloc[0]
        return {
            'date': date,
            'is_trading_day': True,
            'market_open': row['market_open'].strftime('%Y-%m-%d %H:%M:%S%z'),
            'market_close': row['market_close'].strftime('%Y-%m-%d %H:%M:%S%z'),
            'exchange': exchange
        }
        
    except Exception as e:
        logger.error(f"Error checking trading day: {e}")
        return {'error': str(e), 'date': date}


def get_next_trading_day(date: str, exchange: str = "NYSE") -> Dict[str, Any]:
    """
    获取下一个交易日
    
    Args:
        date: 起始日期（YYYY-MM-DD）
        exchange: 交易所代码
        
    Returns:
        下一个交易日信息
    """
    try:
        start = datetime.strptime(date, '%Y-%m-%d')
        end = start + timedelta(days=10)  # Look ahead 10 days
        
        calendar = mcal.get_calendar(exchange)
        schedule = calendar.schedule(
            start_date=start.strftime('%Y-%m-%d'),
            end_date=end.strftime('%Y-%m-%d')
        )
        
        if not schedule.empty:
            next_day = schedule.index[0]
            row = schedule.iloc[0]
            
            return {
                'date': next_day.strftime('%Y-%m-%d'),
                'is_trading_day': True,
                'market_open': row['market_open'].strftime('%Y-%m-%d %H:%M:%S%z'),
                'market_close': row['market_close'].strftime('%Y-%m-%d %H:%M:%S%z'),
                'exchange': exchange
            }
        
        return {'error': 'No trading day found in next 10 days'}
        
    except Exception as e:
        logger.error(f"Error getting next trading day: {e}")
        return {'error': str(e)}


def get_previous_trading_day(date: str, exchange: str = "NYSE") -> Dict[str, Any]:
    """
    获取上一个交易日
    
    Args:
        date: 起始日期（YYYY-MM-DD）
        exchange: 交易所代码
        
    Returns:
        上一个交易日信息
    """
    try:
        end = datetime.strptime(date, '%Y-%m-%d')
        start = end - timedelta(days=10)  # Look back 10 days
        
        calendar = mcal.get_calendar(exchange)
        schedule = calendar.schedule(
            start_date=start.strftime('%Y-%m-%d'),
            end_date=end.strftime('%Y-%m-%d')
        )
        
        if not schedule.empty:
            prev_day = schedule.index[-1]
            row = schedule.iloc[-1]
            
            return {
                'date': prev_day.strftime('%Y-%m-%d'),
                'is_trading_day': True,
                'market_open': row['market_open'].strftime('%Y-%m-%d %H:%M:%S%z'),
                'market_close': row['market_close'].strftime('%Y-%m-%d %H:%M:%S%z'),
                'exchange': exchange
            }
        
        return {'error': 'No trading day found in previous 10 days'}
        
    except Exception as e:
        logger.error(f"Error getting previous trading day: {e}")
        return {'error': str(e)}


def count_trading_days(start_date: str, end_date: str, exchange: str = "NYSE") -> Dict[str, Any]:
    """
    计算两个日期之间的交易日数量
    
    Args:
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        exchange: 交易所代码
        
    Returns:
        交易日数量信息
    """
    try:
        calendar = mcal.get_calendar(exchange)
        schedule = calendar.schedule(start_date=start_date, end_date=end_date)
        
        count = len(schedule)
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'trading_days': count,
            'exchange': exchange
        }
        
    except Exception as e:
        logger.error(f"Error counting trading days: {e}")
        return {'error': str(e)}
