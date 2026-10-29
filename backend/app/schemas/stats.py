"""What the admin dashboard endpoint returns."""

import uuid
from datetime import date, datetime

from app.schemas.common import CamelModel, Money


class DayCount(CamelModel):
    date: date
    orders: int


class TopProduct(CamelModel):
    id: int
    name: str
    image: str
    sold: int


class LowStockProduct(CamelModel):
    id: int
    name: str
    image: str
    stock: int


class RecentOrder(CamelModel):
    id: uuid.UUID
    order_number: str
    full_name: str
    total: Money
    status: str
    created_at: datetime


class DashboardStats(CamelModel):
    revenue: Money  # delivered orders
    awaiting_payment: Money  # confirmed, processing or shipped
    average_order: Money  # delivered orders
    return_rate: float | None  # of delivered or returned; null before any finished
    customers: int  # distinct phone numbers
    status_counts: dict[str, int]
    orders_per_day: list[DayCount]  # the last 14 days, shop time
    top_products: list[TopProduct]
    low_stock: list[LowStockProduct]
    recent_orders: list[RecentOrder]
