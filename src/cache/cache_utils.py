"""
Caching utilities for market data
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from functools import wraps
from src.cache.db_manager import DatabaseManager
from src.logger import logger


class KlineCache:
    """Helper class to manage K-line data caching logic"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_cached_data(self, symbol: str, bar_size: str) -> List[Dict[str, Any]]:
        """Get cached K-line data
        
        Args:
            symbol: Stock symbol
            bar_size: Bar size
            
        Returns:
            List of cached bars (empty list if none)
        """
        df = self.db.get_kline_data(symbol, bar_size)
        if df.empty:
            return []
        
        # Convert DataFrame to list of dicts
        data = df.to_dict('records')
        
        # Normalize datetime to ISO string format for consistency
        for item in data:
            if 'datetime' in item and hasattr(item['datetime'], 'isoformat'):
                item['datetime'] = item['datetime'].isoformat()
        
        return data
    
    def is_cache_fresh(self, symbol: str, bar_size: str, max_age_days: int = 1) -> bool:
        """Check if cached data is fresh enough
        
        Args:
            symbol: Stock symbol
            bar_size: Bar size
            max_age_days: Maximum age in days to consider fresh
            
        Returns:
            True if cache is fresh, False otherwise
        """
        latest_cached = self.db.get_latest_kline_datetime(symbol, bar_size)
        if not latest_cached:
            return False
        
        latest_dt = datetime.fromisoformat(latest_cached)
        now = datetime.now()
        age_days = (now - latest_dt).days
        
        return age_days < max_age_days
    
    def get_incremental_duration(self, symbol: str, bar_size: str) -> Optional[str]:
        """Calculate duration string for fetching incremental data
        
        Args:
            symbol: Stock symbol
            bar_size: Bar size
            
        Returns:
            Duration string (e.g., "5 D") or None if no cached data
        """
        latest_cached = self.db.get_latest_kline_datetime(symbol, bar_size)
        if not latest_cached:
            return None
        
        latest_dt = datetime.fromisoformat(latest_cached)
        now = datetime.now()
        days_diff = (now - latest_dt).days + 1
        
        return f"{days_diff} D"
    
    def merge_data(
        self, 
        cached_data: List[Dict[str, Any]], 
        new_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge new data with cached data, removing duplicates
        
        Args:
            cached_data: Existing cached data
            new_data: New data to merge
            
        Returns:
            Merged and sorted data
        """
        if not new_data:
            return cached_data
        
        # Normalize datetime format for comparison
        def normalize_datetime(dt):
            """Convert datetime to ISO string for comparison"""
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            elif isinstance(dt, str):
                # Parse string datetime and convert back to ISO format
                # This handles both '2023-01-02' and '2023-01-02T00:00:00' formats
                try:
                    from datetime import datetime
                    parsed = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                    return parsed.isoformat()
                except:
                    return dt
            return str(dt)
        
        # Create set of existing dates for deduplication (normalized)
        existing_dates = {normalize_datetime(item['datetime']) for item in cached_data}
        
        # Add new bars that don't exist
        merged_data = cached_data.copy()
        for bar in new_data:
            bar_dt = normalize_datetime(bar['datetime'])
            if bar_dt not in existing_dates:
                merged_data.append(bar)
                existing_dates.add(bar_dt)  # Add to set to avoid duplicates in new_data
        
        # Sort by datetime (normalize for comparison)
        merged_data.sort(key=lambda x: normalize_datetime(x['datetime']))
        
        return merged_data
    
    def save_data(self, symbol: str, bar_size: str, data: List[Dict[str, Any]]) -> int:
        """Save K-line data to cache
        
        Args:
            symbol: Stock symbol
            bar_size: Bar size
            data: List of bar data
            
        Returns:
            Number of bars saved
        """
        # Convert dict list to tuple list for database
        bars = [
            (
                bar['datetime'],
                bar['open'],
                bar['high'],
                bar['low'],
                bar['close'],
                bar['volume'],
                bar.get('average', 0),
                bar.get('bar_count', 0)
            )
            for bar in data
        ]
        
        return self.db.save_kline_data(symbol, bar_size, bars)


def _has_error(data: Any) -> bool:
    """Check if data contains error information
    
    Args:
        data: Data to check
        
    Returns:
        True if data contains error, False otherwise
    """
    if not data:
        return False
    
    # Check if it's a list/iterable
    if isinstance(data, (list, tuple)):
        # Check if any item has 'error' key
        return any(isinstance(item, dict) and 'error' in item for item in data)
    
    # Check if it's a single dict with error
    if isinstance(data, dict):
        return 'error' in data
    
    return False


def with_kline_cache(
    use_cache_param: str = 'use_cache',
    force_refresh_param: str = 'force_refresh',
    symbol_param: str = 'symbol',
    bar_size_param: str = 'bar_size'
):
    """Decorator to add caching logic to K-line data fetching functions
    
    This decorator handles:
    - Checking cache freshness
    - Returning cached data if fresh
    - Fetching incremental data if cache is stale
    - Merging and saving data
    
    Args:
        use_cache_param: Name of the use_cache parameter
        force_refresh_param: Name of the force_refresh parameter
        symbol_param: Name of the symbol parameter
        bar_size_param: Name of the bar_size parameter
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract parameters
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            params = bound_args.arguments
            
            use_cache = params.get(use_cache_param, True)
            force_refresh = params.get(force_refresh_param, False)
            symbol = params.get(symbol_param)
            bar_size = params.get(bar_size_param)
            
            if not symbol or not bar_size:
                # If required params missing, just call original function
                return await func(*args, **kwargs)
            
            # Initialize cache helper
            from src.cache.db_manager import DatabaseManager
            cache = KlineCache(DatabaseManager())
            
            # If not using cache or forcing refresh, call original function
            if not use_cache or force_refresh:
                logger.info(f"Fetching fresh data for {symbol} (cache disabled)")
                result = await func(*args, **kwargs)
                
                # Save to cache if use_cache is True
                if use_cache and result and not _has_error(result):
                    saved = cache.save_data(symbol, bar_size, result)
                    logger.info(f"Cached {saved} bars for {symbol}")
                
                return result
            
            # Check cache
            cached_data = cache.get_cached_data(symbol, bar_size)
            
            if not cached_data:
                logger.info(f"No cached data for {symbol}, fetching full history")
                result = await func(*args, **kwargs)
                
                if result and not _has_error(result):
                    cache.save_data(symbol, bar_size, result)
                    logger.info(f"Cached {len(result)} bars for {symbol}")
                
                return result
            
            # Check cache freshness
            if cache.is_cache_fresh(symbol, bar_size):
                logger.info(f"Cache is fresh, returning {len(cached_data)} bars for {symbol}")
                return cached_data
            
            # Fetch incremental data
            logger.info(f"Cache is stale for {symbol}, fetching incremental data")
            inc_duration = cache.get_incremental_duration(symbol, bar_size)
            
            # Convert all parameters to kwargs to avoid duplicate argument error
            modified_params = params.copy()
            modified_params['duration'] = inc_duration
            
            # Call original function with modified duration (all as kwargs)
            new_data = await func(**modified_params)
            
            if new_data and not _has_error(new_data):
                # Merge and save
                merged_data = cache.merge_data(cached_data, new_data)
                cache.save_data(symbol, bar_size, new_data)
                logger.info(f"Updated cache with {len(new_data)} new bars")
                return merged_data
            
            # If fetching new data failed, return cached data
            logger.warning(f"Failed to fetch new data, returning cached data")
            return cached_data
        
        return wrapper
    return decorator
