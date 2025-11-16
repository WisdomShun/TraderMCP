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
    currency: Optional[str] = Field(None, description="币种")

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
    position: float = Field(description="持仓数量")
    market_price: float = Field(description="市场价格")
    market_value: float = Field(description="市场价值")
    average_cost: float = Field(description="平均成本")
    unrealized_pnl: float = Field(description="未实现盈亏")
    realized_pnl: float = Field(description="已实现盈亏")

class PositionOption(BaseModel):
    """期权仓位模型"""
    detail: OptionInfo = Field(description="期权详情")
    position: float = Field(description="持仓数量")
    market_price: float = Field(description="市场价格")
    market_value: float = Field(description="市场价值")
    average_cost: float = Field(description="平均成本")
    unrealized_pnl: float = Field(description="未实现盈亏")
    realized_pnl: float = Field(description="已实现盈亏")

class PositionSummary(BaseModel):
    """仓位汇总模型"""
    stock_positions: List[PositionStock] = Field(default_factory=list, description="股票仓位列表")
    option_positions: List[PositionOption] = Field(default_factory=list, description="期权仓位列表")

    total_market_value: float = Field(description="总市值", default=0)
    stock_market_value: float = Field(description="股票市值", default=0)
    option_market_value: float = Field(description="期权市值", default=0)

    total_unrealized_pnl: float = Field(description="总未实现盈亏", default=0)
    total_realized_pnl: float = Field(description="总已实现盈亏", default=0)


class AccountSummary(BaseModel):
    """账户摘要模型（完整的账户信息）"""
    
    # 账户基本信息
    account_or_group: str = Field(description="账户名称/编号")
    currency: str = Field(description="账户币种")
    real_currency: str = Field(description="实际币种")
    exchange_rate: float = Field(default=1.0, description="汇率")
    
    # 现金相关
    cash_balance: float = Field(default=0.0, description="现金余额")
    total_cash_balance: float = Field(default=0.0, description="总现金余额")
    accrued_cash: float = Field(default=0.0, description="应计现金（利息等）")
    fx_cash_balance: float = Field(default=0.0, description="外汇现金余额")
    
    # 持仓市值
    stock_market_value: float = Field(default=0.0, description="股票市值")
    option_market_value: float = Field(default=0.0, description="期权市值")
    future_option_value: float = Field(default=0.0, description="期货期权市值")
    warrant_value: float = Field(default=0.0, description="权证价值")
    issuer_option_value: float = Field(default=0.0, description="发行人期权价值")
    
    # 基金和债券
    fund_value: float = Field(default=0.0, description="基金价值")
    mutual_fund_value: float = Field(default=0.0, description="共同基金价值")
    money_market_fund_value: float = Field(default=0.0, description="货币市场基金价值")
    corporate_bond_value: float = Field(default=0.0, description="公司债券价值")
    t_bond_value: float = Field(default=0.0, description="国债价值")
    t_bill_value: float = Field(default=0.0, description="短期国债价值")
    
    # 净值和盈亏
    net_liquidation: float = Field(default=0.0, description="净清算价值（总资产）")
    unrealized_pnl: float = Field(default=0.0, description="未实现盈亏")
    realized_pnl: float = Field(default=0.0, description="已实现盈亏")
    futures_pnl: float = Field(default=0.0, description="期货盈亏")
    net_dividend: float = Field(default=0.0, description="净股息")
    
    @property
    def total_market_value(self) -> float:
        """计算总持仓市值（不含现金）"""
        return (
            self.stock_market_value +
            self.option_market_value +
            self.future_option_value +
            self.warrant_value +
            self.issuer_option_value +
            self.fund_value +
            self.mutual_fund_value +
            self.money_market_fund_value +
            self.corporate_bond_value +
            self.t_bond_value +
            self.t_bill_value
        )
    
    @property
    def cash_percentage(self) -> float:
        """现金占比"""
        if self.net_liquidation == 0:
            return 0.0
        return (self.total_cash_balance / self.net_liquidation) * 100
    
    @property
    def invested_percentage(self) -> float:
        """投资占比"""
        if self.net_liquidation == 0:
            return 0.0
        return (self.total_market_value / self.net_liquidation) * 100



class BidAskSpread(BaseModel):
    """买卖价差模型"""
    symbol: str = Field(description="股票代码")
    bid: Optional[float] = Field(None, description="买一价")
    ask: Optional[float] = Field(None, description="卖一价")
    spread: Optional[float] = Field(None, description="价差")
    spread_pct: Optional[float] = Field(None, description="价差百分比")
    time: Optional[str] = Field(None, description="时间戳")
