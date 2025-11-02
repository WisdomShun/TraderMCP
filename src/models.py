"""
Pydantic models for business logic wrappers
用于包装 ib_insync 原生对象，提供计算后的业务指标
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class StockInfo(BaseModel):
    """股票信息模型"""
    symbol: str = Field(description="股票代码")
    exchange: Optional[str] = Field(None, description="交易所")

class OptionInfo(BaseModel):
    """期权信息模型"""
    symbol: str = Field(description="标的股票代码")
    exchange: Optional[str] = Field(None, description="交易所")
    right: str = Field(description="看涨/看跌 (C/P)")
    strike: float = Field(description="行权价")
    expiry: datetime = Field(description="到期日")

class PositionStock(BaseModel):
    """股票仓位模型"""
    detail: StockInfo = Field(description="股票详情")
    position: int = Field(description="持仓数量")
    market_price: float = Field(description="市场价格")
    market_value: float = Field(description="市场价值")
    average_cost: float = Field(description="平均成本")
    unrealized_pnl: float = Field(description="未实现盈亏")
    realized_pnl: float = Field(description="已实现盈亏")

class PositionOption(BaseModel):
    """期权仓位模型"""
    detail: OptionInfo = Field(description="期权详情")
    position: int = Field(description="持仓数量")
    market_price: float = Field(description="市场价格")
    market_value: float = Field(description="市场价值")
    average_cost: float = Field(description="平均成本")
    unrealized_pnl: float = Field(description="未实现盈亏")
    realized_pnl: float = Field(description="已实现盈亏")

class PositionSummary(BaseModel):
    """仓位汇总模型"""
    stock_positions: List[PositionStock] = Field(default_factory=list, description="股票仓位列表")
    option_positions: List[PositionOption] = Field(default_factory=list, description="期权仓位列表")

    total_market_value: float = Field(description="总市值")
    stock_market_value: float = Field(description="股票市值")
    option_market_value: float = Field(description="期权市值")

    total_unrealized_pnl: float = Field(description="总未实现盈亏")
    total_realized_pnl: float = Field(description="总已实现盈亏")


class AccountSummary(BaseModel):
    """账户摘要模型（计算后的关键指标）"""
    account: str = Field(description="账户号")
    net_liquidation: float = Field(description="净资产")
    gross_position_value: float = Field(description="总持仓价值")

    maint_margin_req: float = Field(description="维持保证金")
    available_funds: float = Field(description="可用资金")
    excess_liquidity: float = Field(description="超额流动性")
    buying_power: float = Field(description="购买力")
    init_margin_req: float = Field(description="初始保证金")
    leverage: float = Field(description="杠杆率")

    total_cash: float = Field(description="现金总额")
    currency: str = Field(default="USD", description="币种")
    settled_cash: float = Field(description="已结算现金")
    cash_balance: float = Field(description="现金余额")



class OrderResult(BaseModel):
    """下单结果模型"""
    success: bool = Field(description="是否成功")
    order_id: Optional[int] = Field(None, description="订单ID")
    symbol: str = Field(description="标的符号")
    action: Optional[str] = Field(None, description="操作方向")
    quantity: Optional[int] = Field(None, description="数量")
    order_type: Optional[str] = Field(None, description="订单类型")
    warnings: List[str] = Field(default_factory=list, description="警告信息")
    error: Optional[str] = Field(None, description="错误信息")
    risk_issues: Optional[str] = Field(None, description="风控问题")


class ModifyOrderResult(BaseModel):
    """修改订单结果"""
    success: bool
    order_id: int
    new_quantity: Optional[int] = None
    new_price: Optional[float] = None
    error: Optional[str] = None


class CancelOrderResult(BaseModel):
    """取消订单结果"""
    success: bool
    order_id: int
    message: Optional[str] = None
    error: Optional[str] = None


class BidAskSpread(BaseModel):
    """买卖价差模型"""
    symbol: str = Field(description="股票代码")
    bid: Optional[float] = Field(None, description="买一价")
    ask: Optional[float] = Field(None, description="卖一价")
    spread: Optional[float] = Field(None, description="价差")
    spread_pct: Optional[float] = Field(None, description="价差百分比")
    time: Optional[str] = Field(None, description="时间戳")
