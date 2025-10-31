"""
Option trading tools
"""
from typing import List, Dict, Any, Optional
from src.ib_client import get_ib_client
from src.cache.db_manager import DatabaseManager
from src.logger import logger

ib_client = get_ib_client()
db = DatabaseManager()


async def get_option_chain(
    symbol: str,
    expiration_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    获取期权链数据
    
    Args:
        symbol: 标的股票代码
        expiration_date: 到期日过滤（可选，格式：YYYYMMDD）
        
    Returns:
        期权链列表，包含合约信息、希腊值、隐含波动率等
    """
    try:
        logger.info(f"Fetching option chain for {symbol}...")
        
        # Get option chain from IB
        chain_data = await ib_client.get_option_chain(symbol)
        
        if not chain_data:
            logger.warning(f"No option chain found for {symbol}")
            return []
        
        # Filter by expiration if provided
        if expiration_date:
            chain_data = [opt for opt in chain_data if opt['expiration'] == expiration_date]
        
        # Get detailed data with Greeks for each option
        detailed_options = []
        
        # Limit the number of options to fetch (to avoid rate limiting)
        max_options = 50
        count = 0
        
        for opt_info in chain_data:
            if count >= max_options:
                logger.warning(f"Reached max options limit ({max_options}), returning partial data")
                break
            
            try:
                # Create option contract for both CALL and PUT
                for right in ['C', 'P']:
                    option_contract = ib_client.create_option_contract(
                        symbol=symbol,
                        expiration=opt_info['expiration'],
                        strike=opt_info['strike'],
                        right=right,
                        exchange=opt_info.get('exchange', 'SMART')
                    )
                    
                    # Get Greeks and market data
                    greeks_data = await ib_client.get_option_greeks(option_contract)
                    
                    if greeks_data:
                        detailed_options.append(greeks_data)
                        count += 1
                    
            except Exception as e:
                logger.error(f"Error fetching option details: {e}")
                continue
        
        # Cache the option data
        if detailed_options:
            db.save_option_chain(detailed_options)
            logger.info(f"Cached {len(detailed_options)} option contracts")
        
        logger.info(f"Retrieved {len(detailed_options)} option contracts for {symbol}")
        return detailed_options
        
    except Exception as e:
        logger.error(f"Error getting option chain: {e}")
        return [{'error': str(e)}]


async def get_option_greeks(
    symbol: str,
    expiration: str,
    strike: float,
    right: str
) -> Dict[str, Any]:
    """
    获取单个期权合约的希腊值和市场数据
    
    Args:
        symbol: 标的股票代码
        expiration: 到期日（YYYYMMDD）
        strike: 执行价
        right: 期权类型（'C' for Call, 'P' for Put）
        
    Returns:
        期权详细数据，包含Delta、Gamma、Theta、Vega、隐含波动率等
    """
    try:
        logger.info(f"Fetching Greeks for {symbol} {expiration} {strike} {right}...")
        
        option_contract = ib_client.create_option_contract(
            symbol=symbol,
            expiration=expiration,
            strike=strike,
            right=right
        )
        
        greeks_data = await ib_client.get_option_greeks(option_contract)
        
        if not greeks_data:
            logger.error("Failed to get option Greeks")
            return {'error': 'Failed to fetch option data'}
        
        logger.info(f"Retrieved Greeks for {symbol} option")
        return greeks_data
        
    except Exception as e:
        logger.error(f"Error getting option Greeks: {e}")
        return {'error': str(e)}


async def get_cached_option_chain(
    symbol: str,
    expiration_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    从缓存获取期权链数据（不请求IB）
    
    Args:
        symbol: 标的股票代码
        expiration_date: 到期日过滤（可选）
        
    Returns:
        缓存的期权链数据
    """
    try:
        logger.info(f"Fetching cached option chain for {symbol}...")
        options = db.get_option_chain(symbol, expiration_date)
        logger.info(f"Retrieved {len(options)} cached options")
        return options
        
    except Exception as e:
        logger.error(f"Error getting cached option chain: {e}")
        return [{'error': str(e)}]


async def search_options_by_delta(
    symbol: str,
    target_delta: float,
    delta_range: float = 0.05,
    expiration_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    根据Delta值搜索期权
    
    Args:
        symbol: 标的股票代码
        target_delta: 目标Delta值
        delta_range: Delta容差范围（默认±0.05）
        expiration_date: 到期日过滤（可选）
        
    Returns:
        符合Delta条件的期权列表
    """
    try:
        # Try to get from cache first
        options = db.get_option_chain(symbol, expiration_date)
        
        # If no cache, fetch from IB
        if not options:
            logger.info("No cached data, fetching from IB...")
            options = await get_option_chain(symbol, expiration_date)
        
        # Filter by delta
        filtered = []
        for opt in options:
            delta = opt.get('delta')
            if delta is not None:
                if abs(delta - target_delta) <= delta_range:
                    filtered.append(opt)
        
        logger.info(f"Found {len(filtered)} options with delta ≈ {target_delta}")
        return filtered
        
    except Exception as e:
        logger.error(f"Error searching options by delta: {e}")
        return [{'error': str(e)}]
