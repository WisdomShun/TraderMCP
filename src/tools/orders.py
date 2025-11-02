"""
Order management tools (query, place, modify, cancel)
"""
from typing import List, Optional
from datetime import datetime, timedelta
from ib_insync import Trade
from src.ib_client import get_ib_client
from src.cache.db_manager import DatabaseManager
from src.logger import logger
from src.config import get_config
from src.risk.risk_manager import get_risk_manager
from src.models import OrderResult, ModifyOrderResult, CancelOrderResult
import json

ib_client = get_ib_client()
db = DatabaseManager()
risk_manager = get_risk_manager()
config = get_config()


async def get_open_orders() -> List[Trade]:
    """
    获取当前未成交订单（返回 ib_insync Trade 对象列表）
    
    Returns:
        Trade 对象列表，包含以下属性：
        - contract: 合约信息
        - order: 订单详情（orderId, action, totalQuantity, orderType 等）
        - orderStatus: 订单状态（status, filled, remaining 等）
        - log: 订单日志
    """
    try:
        logger.info("Fetching open orders...")
        trades = await ib_client.get_open_orders()
        logger.info(f"Retrieved {len(trades)} open orders")
        return trades
        
    except Exception as e:
        logger.error(f"Error getting open orders: {e}")
        return []


async def get_order_history(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 7
) -> List[Trade]:
    """
    获取历史订单（返回 ib_insync Trade 对象列表）
    
    注意：IB API 只能获取当前会话的订单历史，无法获取历史会话的订单
    
    Args:
        symbol: 股票代码过滤（可选）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        days: 查询天数（默认7天，仅供参考）
        
    Returns:
        Trade 对象列表
    """
    try:
        logger.info(f"Fetching order history (symbol={symbol}, days={days})...")
        
        # Get all trades from IB (includes filled and partially filled)
        all_trades = await ib_client.get_trades()
        
        # Filter by symbol if provided
        if symbol:
            all_trades = [t for t in all_trades if t.contract.symbol == symbol]
        
        # Note: Time-based filtering would require accessing trade execution time
        # which is in the fills. For simplicity, we return all trades.
        # If strict date filtering is needed, it should be done on the fills.
        
        logger.info(f"Retrieved {len(all_trades)} trades")
        return all_trades
        
    except Exception as e:
        logger.error(f"Error getting order history: {e}")
        return []


async def get_order_by_id(order_id: int) -> Optional[Trade]:
    """
    根据订单ID获取订单详情（返回 Trade 对象）
    
    Args:
        order_id: 订单ID
        
    Returns:
        Trade 对象或 None
    """
    try:
        # Get all trades (open + filled)
        all_trades = await ib_client.get_trades()
        
        # Find trade with matching order ID
        for trade in all_trades:
            if trade.order.orderId == order_id:
                return trade
        
        logger.warning(f"Order {order_id} not found")
        return None
        
    except Exception as e:
        logger.error(f"Error getting order by ID: {e}")
        return None


def _log_trading_operation(
    operation: str,
    symbol: str,
    reason: str,
    risk_checks: list,
    result: str,
    order_type: Optional[str] = None,
    action: Optional[str] = None,
    quantity: Optional[int] = None,
    price: Optional[float] = None,
    stop_loss: Optional[float] = None,
    order_id: Optional[str] = None,
    error_message: Optional[str] = None
):
    """
    记录交易操作到数据库和日志文件
    
    Args:
        operation: 操作类型
        symbol: 股票代码
        reason: 操作原因（AI提供）
        risk_checks: 风控检查结果列表
        result: 操作结果
        ... 其他订单参数
    """
    # Convert risk checks to dict
    risk_checks_dict = {
        'checks': [check.to_dict() for check in risk_checks],
        'has_blocking': any(check.level.value == 'block' for check in risk_checks),
        'has_warnings': any(check.level.value == 'warning' for check in risk_checks)
    }
    
    # Log to database
    if True:  # Always log trading to database
        db.log_trading_operation(
            operation=operation,
            symbol=symbol,
            reason=reason,
            order_type=order_type,
            action=action,
            quantity=quantity,
            price=price,
            stop_loss=stop_loss,
            risk_checks=risk_checks_dict,
            result=result,
            order_id=order_id,
            error_message=error_message
        )
    
    # Log to file (human-readable format)
    if True:  # Always log trading to file
        log_path = config.log_dir / f"trading_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"操作: {operation}\n")
            f.write(f"标的: {symbol}\n")
            if order_type:
                f.write(f"订单类型: {order_type}\n")
            if action:
                f.write(f"方向: {action}\n")
            if quantity:
                f.write(f"数量: {quantity}\n")
            if price:
                f.write(f"价格: {price}\n")
            if stop_loss:
                f.write(f"止损价: {stop_loss}\n")
            f.write(f"原因: {reason}\n")
            f.write(f"\n风控检查:\n")
            for check in risk_checks:
                f.write(f"  - [{check.level.value.upper()}] {check.check_name}: {check.message}\n")
            f.write(f"\n结果: {result}\n")
            if order_id:
                f.write(f"订单ID: {order_id}\n")
            if error_message:
                f.write(f"错误信息: {error_message}\n")
            f.write(f"{'='*80}\n")


async def place_order(
    symbol: str,
    action: str,
    quantity: int,
    order_type: str,
    reason: str,
    limit_price: Optional[float] = None,
    stop_loss_price: Optional[float] = None,
    take_profit_price: Optional[float] = None,
    contract_type: str = "STK",
    option_details: Optional[dict] = None
) -> OrderResult:
    """
    下单（带风控检查和日志记录）
    
    Args:
        symbol: 股票代码
        action: 买卖方向 (BUY/SELL)
        quantity: 数量
        order_type: 订单类型 (MKT=市价, LMT=限价, STP=止损, STP LMT=止损限价)
        reason: 下单原因（AI必须提供）
        limit_price: 限价（限价单必需）
        stop_loss_price: 止损价（开仓必需）
        take_profit_price: 止盈价（可选）
        contract_type: 合约类型 (STK=股票, OPT=期权)
        option_details: 期权详情（期权订单必需）
        
    Returns:
        OrderResult: 订单结果模型
    """
    try:
        logger.info(f"Placing order: {action} {quantity} {symbol} @ {order_type}")
        
        # Validate inputs
        if not reason or reason.strip() == "":
            return OrderResult(
                success=False,
                error='Order reason is required (must be provided by AI)',
                symbol=symbol
            )
        
        if action not in ['BUY', 'SELL']:
            return OrderResult(
                success=False,
                error=f'Invalid action: {action}. Must be BUY or SELL',
                symbol=symbol
            )
        
        if order_type not in ['MKT', 'LMT', 'STP', 'STP LMT']:
            return OrderResult(
                success=False,
                error=f'Invalid order type: {order_type}',
                symbol=symbol
            )
        
        # Get account and position data for risk checks
        account_summary = await ib_client.get_account_summary()
        current_positions = await ib_client.get_portfolio()
        
        # Determine price for risk calculations
        check_price = limit_price
        if not check_price and order_type == 'MKT':
            # Get current market price for risk calculation
            price_data = await ib_client.get_market_price(
                ib_client.create_stock_contract(symbol)
            )
            check_price = price_data.get('last') if price_data else None
        
        # Run risk checks
        risk_checks = risk_manager.check_all(
            operation='place_order',
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=check_price,
            stop_loss=stop_loss_price,
            account_summary=account_summary,
            current_positions=current_positions,
            contract_type=contract_type,
            option_details=option_details
        )
        
        # Check for blocking issues
        if risk_manager.has_blocking_issues(risk_checks):
            blocking_checks = [c for c in risk_checks if c.level.value == 'block']
            error_msg = '; '.join([c.message for c in blocking_checks])
            
            # Log failed order
            _log_trading_operation(
                operation='place_order',
                symbol=symbol,
                reason=reason,
                risk_checks=risk_checks,
                result='blocked_by_risk',
                order_type=order_type,
                action=action,
                quantity=quantity,
                price=check_price,
                stop_loss=stop_loss_price,
                error_message=error_msg
            )
            
            return OrderResult(
                success=False,
                error='Order blocked by risk checks',
                risk_issues=error_msg,
                symbol=symbol
            )
        
        # Get warnings (if any)
        warnings = risk_manager.get_warnings(risk_checks)
        warning_messages = [w.message for w in warnings] if warnings else []
        
        # Create contract
        if contract_type == "STK":
            contract = ib_client.create_stock_contract(symbol)
        elif contract_type == "OPT":
            if not option_details:
                return OrderResult(
                    success=False,
                    error='Option details required for option orders',
                    symbol=symbol
                )
            contract = ib_client.create_option_contract(
                symbol=symbol,
                expiration=option_details['expiration'],
                strike=option_details['strike'],
                right=option_details['right']
            )
        else:
            return OrderResult(
                success=False,
                error=f'Unsupported contract type: {contract_type}',
                symbol=symbol
            )
        
        # Place order with bracket (if stop loss or take profit provided)
        if stop_loss_price or take_profit_price:
            # Use bracket order
            trades = await ib_client.place_bracket_order(
                contract=contract,
                action=action,
                quantity=quantity,
                entry_price=limit_price if order_type == 'LMT' else None,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price
            )
            
            if not trades:
                _log_trading_operation(
                    operation='place_order',
                    symbol=symbol,
                    reason=reason,
                    risk_checks=risk_checks,
                    result='failed',
                    order_type=order_type,
                    action=action,
                    quantity=quantity,
                    price=limit_price,
                    stop_loss=stop_loss_price,
                    error_message='Failed to place bracket order'
                )
                
                return OrderResult(
                    success=False,
                    error='Failed to place bracket order',
                    symbol=symbol
                )
            
            order_id = trades[0].order.orderId
            
        else:
            # Regular order
            trade = await ib_client.place_simple_order(
                contract=contract,
                action=action,
                quantity=quantity,
                order_type=order_type,
                limit_price=limit_price,
                stop_price=stop_loss_price if order_type in ['STP', 'STP LMT'] else None
            )
            
            if not trade:
                _log_trading_operation(
                    operation='place_order',
                    symbol=symbol,
                    reason=reason,
                    risk_checks=risk_checks,
                    result='failed',
                    order_type=order_type,
                    action=action,
                    quantity=quantity,
                    price=limit_price,
                    stop_loss=stop_loss_price,
                    error_message='Failed to place order'
                )
                
                return OrderResult(
                    success=False,
                    error='Failed to place order',
                    symbol=symbol
                )
            
            order_id = trade.order.orderId
        
        # Log successful order
        _log_trading_operation(
            operation='place_order',
            symbol=symbol,
            reason=reason,
            risk_checks=risk_checks,
            result='success',
            order_type=order_type,
            action=action,
            quantity=quantity,
            price=limit_price,
            stop_loss=stop_loss_price,
            order_id=str(order_id)
        )
        
        logger.info(f"Order placed successfully: ID={order_id}")
        
        return OrderResult(
            success=True,
            order_id=order_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type=order_type,
            warnings=warning_messages
        )
        
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        
        # Log error
        _log_trading_operation(
            operation='place_order',
            symbol=symbol,
            reason=reason,
            risk_checks=[],
            result='error',
            order_type=order_type,
            action=action,
            quantity=quantity,
            price=limit_price,
            stop_loss=stop_loss_price,
            error_message=str(e)
        )
        
        return OrderResult(
            success=False,
            error=str(e),
            symbol=symbol
        )


async def modify_order(
    order_id: int,
    reason: str,
    new_quantity: Optional[int] = None,
    new_price: Optional[float] = None
) -> ModifyOrderResult:
    """
    修改订单
    
    Args:
        order_id: 订单ID
        reason: 修改原因（AI必须提供）
        new_quantity: 新数量（可选）
        new_price: 新价格（可选）
        
    Returns:
        ModifyOrderResult: 修改结果模型
    """
    try:
        logger.info(f"Modifying order {order_id}...")
        
        if not reason or reason.strip() == "":
            return ModifyOrderResult(
                success=False,
                error='Modification reason is required',
                order_id=order_id
            )
        
        # Get order details
        order_info = await get_order_by_id(order_id)
        if not order_info:
            return ModifyOrderResult(
                success=False,
                error=f'Order {order_id} not found',
                order_id=order_id
            )
        
        symbol = order_info.contract.symbol
        
        # Modify order
        success = await ib_client.modify_simple_order(
            trade=order_info,
            new_quantity=new_quantity,
            new_price=new_price
        )
        
        # Log operation
        _log_trading_operation(
            operation='modify_order',
            symbol=symbol,
            reason=reason,
            risk_checks=[],
            result='success' if success else 'failed',
            order_id=str(order_id),
            quantity=new_quantity,
            price=new_price,
            error_message=None if success else 'Modification failed'
        )
        
        if success:
            logger.info(f"Order {order_id} modified successfully")
            return ModifyOrderResult(
                success=True,
                order_id=order_id,
                new_quantity=new_quantity,
                new_price=new_price
            )
        else:
            return ModifyOrderResult(
                success=False,
                error='Failed to modify order',
                order_id=order_id
            )
        
    except Exception as e:
        logger.error(f"Error modifying order: {e}")
        
        _log_trading_operation(
            operation='modify_order',
            symbol='UNKNOWN',
            reason=reason,
            risk_checks=[],
            result='error',
            order_id=str(order_id),
            error_message=str(e)
        )
        
        return ModifyOrderResult(
            success=False,
            error=str(e),
            order_id=order_id
        )


async def cancel_order(order_id: int, reason: str) -> CancelOrderResult:
    """
    取消订单
    
    Args:
        order_id: 订单ID
        reason: 取消原因（AI必须提供）
        
    Returns:
        CancelOrderResult: 取消结果模型
    """
    try:
        logger.info(f"Cancelling order {order_id}...")
        
        if not reason or reason.strip() == "":
            return CancelOrderResult(
                success=False,
                error='Cancellation reason is required',
                order_id=order_id
            )
        
        # Get order details
        order_trade = await get_order_by_id(order_id)
        if not order_trade:
            return CancelOrderResult(
                success=False,
                error=f'Order {order_id} not found',
                order_id=order_id
            )
        
        symbol = order_trade.contract.symbol
        
        # Cancel order
        success = await ib_client.cancel_order(order_trade.order)
        
        # Log operation
        _log_trading_operation(
            operation='cancel_order',
            symbol=symbol,
            reason=reason,
            risk_checks=[],
            result='success' if success else 'failed',
            order_id=str(order_id),
            error_message=None if success else 'Cancellation failed'
        )
        
        if success:
            logger.info(f"Order {order_id} cancelled successfully")
            return CancelOrderResult(
                success=True,
                order_id=order_id,
                message='Order cancelled'
            )
        else:
            return CancelOrderResult(
                success=False,
                error='Failed to cancel order',
                order_id=order_id
            )
        
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        
        _log_trading_operation(
            operation='cancel_order',
            symbol='UNKNOWN',
            reason=reason,
            risk_checks=[],
            result='error',
            order_id=str(order_id),
            error_message=str(e)
        )
        
        return CancelOrderResult(
            success=False,
            error=str(e),
            order_id=order_id
        )
