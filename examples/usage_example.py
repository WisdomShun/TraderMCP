"""
IBTraderMCP 使用示例
演示如何使用 IBTraderMCP 进行账户查询、数据获取和交易操作
"""
import asyncio
import nest_asyncio
nest_asyncio.apply()

from src.ib_client import get_ib_client
from src.tools.account import get_account_summary
from src.tools.positions import get_stock_positions, get_option_positions, get_position_summary
from src.tools.orders import place_order, get_open_orders, cancel_order
from src.tools.market_data import get_daily_kline
from src.tools.quotes import get_last_price
from src.tools.options import get_option_chain
from src.tools.calendar import get_trading_calendar, is_trading_day
from src.logger import logger

ib_client = get_ib_client()


async def example_account_query():
    """示例：账户查询"""
    print("\n" + "="*80)
    print("示例 1: 账户查询")
    print("="*80)
    
    # 获取账户摘要（返回 AccountSummary Pydantic Model）
    summary = await get_account_summary()
    print(f"\n账户摘要:")
    print(f"  账户: {summary.account}")
    print(f"  净资产: ${summary.net_liquidation:,.2f}")
    print(f"  现金: ${summary.total_cash:,.2f}")
    print(f"  可用资金: ${summary.available_funds:,.2f}")
    print(f"  购买力: ${summary.buying_power:,.2f}")
    
    # 获取仓位（返回 List[PortfolioItem] - ib_insync 原生对象）
    positions = await get_position_summary()
    print(f"\n持仓详情:\n {positions}")

    a = 1
    
    # if positions:
    #     for pos in positions[:5]:  # 显示前5个仓位
    #         # PortfolioItem 属性: contract, position, marketPrice, marketValue, 
    #         # averageCost, unrealizedPNL, realizedPNL, account
    #         symbol = pos.contract.symbol
    #         sec_type = pos.contract.secType
    #         unrealized_pct = (pos.unrealizedPNL / (abs(pos.position) * pos.averageCost) * 100) \
    #             if pos.position != 0 and pos.averageCost != 0 else 0
            
    #         print(f"\n  {symbol} ({sec_type}):")
    #         print(f"    数量: {pos.position}")
    #         print(f"    市值: ${pos.marketValue:,.2f}")
    #         print(f"    盈亏: ${pos.unrealizedPNL:,.2f} ({unrealized_pct:.2f}%)")


async def example_market_data():
    """示例：市场数据查询"""
    print("\n" + "="*80)
    print("示例 2: 市场数据查询")
    print("="*80)
    
    symbol = "AAPL"
    
    # # 获取实时报价（返回 Ticker 对象）
    # ticker = await get_last_price(symbol)
    # if ticker:
    #     print(f"\n{symbol} 实时报价:")
    #     print(f"  最新价: ${ticker.last if ticker.last else 'N/A'}")
    #     print(f"  买价: ${ticker.bid if ticker.bid else 'N/A'}")
    #     print(f"  卖价: ${ticker.ask if ticker.ask else 'N/A'}")
    #     print(f"  时间: {ticker.time}")
    # else:
    #     print(f"⚠️ 无法获取 {symbol} 的报价")
    
    # 获取日K线（最近30天）
    print(f"\n获取 {symbol} 日K线数据...")
    klines = await get_daily_kline(symbol, days=30)
    
    if klines and 'error' not in klines[0]:
        print(f"获取到 {len(klines)} 根K线")
        # 显示最后一根K线
        last_bar = klines[-1]
        print(f"  最后一根K线: {last_bar['datetime']}")
        print(f"    开盘: ${last_bar['open']:.2f}")
        print(f"    最高: ${last_bar['high']:.2f}")
        print(f"    最低: ${last_bar['low']:.2f}")
        print(f"    收盘: ${last_bar['close']:.2f}")
        print(f"    成交量: {last_bar['volume']:,}")


async def example_trading():
    """示例：交易操作"""
    print("\n" + "="*80)
    print("示例 3: 交易操作")
    print("="*80)
    
    symbol = "AAPL"
    
    # # 获取当前价格（返回 Ticker 对象）
    # ticker = await get_last_price(symbol)
    # current_price = ticker.last if ticker and ticker.last else None
    
    # if not current_price:
    #     print("无法获取当前价格，跳过交易示例")
    #     return

    current_price = 250.0
    
    print(f"\n{symbol} 当前价格: ${current_price:.2f}")
    
    # 计算止损价（-5%）
    stop_loss = current_price * 0.95
    
    # # 下单示例（仅演示，不实际执行）
    # print(f"\n演示下单（不实际执行）:")
    # print(f"  标的: {symbol}")
    # print(f"  方向: BUY")
    # print(f"  数量: 10股")
    # print(f"  订单类型: 限价单")
    # print(f"  价格: ${current_price:.2f}")
    # print(f"  止损价: ${stop_loss:.2f}")
    # print(f"  原因: 技术分析显示支撑位强劲，风险回报比合适")
    
    # 如果要实际下单，取消下面的注释
    result = await place_order(
        symbol=symbol,
        action="BUY",
        quantity=10,
        order_type="LMT",
        limit_price=current_price,
        stop_loss_price=stop_loss,
        reason="技术分析显示支撑位强劲，风险回报比合适"
    )
    print(f"\n下单结果: {result}")
    
    # 查询未成交订单
    open_orders = await get_open_orders()
    print(f"\n当前未成交订单数量: {len(open_orders)}")


async def example_options():
    """示例：期权查询"""
    print("\n" + "="*80)
    print("示例 4: 期权查询")
    print("="*80)
    
    symbol = "AAPL"
    
    print(f"\n查询 {symbol} 期权链（可能需要较长时间）...")
    print("注意：期权链查询会受到IB API限流，仅获取部分数据作为演示")
    
    # 获取期权链（限制数量）
    # 实际使用时可以指定到期日
    # options = await get_option_chain(symbol, expiration_date="20250117")
    
    print("\n演示：查找特定Delta的期权")
    print("目标Delta: 0.30 (30 delta)")


async def example_calendar():
    """示例：交易日历"""
    print("\n" + "="*80)
    print("示例 5: 交易日历")
    print("="*80)
    
    from datetime import datetime, timedelta
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 检查今天是否为交易日
    today_info = is_trading_day(today)
    print(f"\n今天 ({today}) 是否为交易日: {today_info['is_trading_day']}")
    
    if today_info['is_trading_day']:
        print(f"  开盘时间: {today_info.get('market_open', 'N/A')}")
        print(f"  收盘时间: {today_info.get('market_close', 'N/A')}")
    
    # 获取本周的交易日
    start_date = today
    end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    calendar = get_trading_calendar(start_date, end_date)
    print(f"\n本周交易日 ({start_date} 到 {end_date}):")
    for day in calendar:
        print(f"  {day['date']}")


async def main():
    """主函数：运行所有示例"""
    try:
        # 连接到 IB Gateway
        print("正在连接到 IB Gateway...")
        connected = await ib_client.connect()
        
        if not connected:
            print("❌ 无法连接到 IB Gateway")
            print("请确保:")
            print("  1. IB Gateway 或 TWS 已启动")
            print("  2. API 连接已启用")
            print("  3. 端口设置正确（模拟盘7497，实盘7496）")
            return
        
        print("✅ 成功连接到 IB Gateway\n")
        
        # 运行示例
        await example_account_query()
        await asyncio.sleep(1)
        
        await example_market_data()
        await asyncio.sleep(1)
        
        await example_trading()
        await asyncio.sleep(1)
        
        # 期权和日历示例（可选）
        # await example_options()
        # await asyncio.sleep(1)
        
        await example_calendar()
        
        print("\n" + "="*80)
        print("所有示例运行完成！")
        print("="*80)
        
    except Exception as e:
        logger.error(f"运行示例时出错: {e}")
        raise
    
    finally:
        # 断开连接
        print("\n正在断开连接...")
        ib_client.disconnect()
        print("已断开连接")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
