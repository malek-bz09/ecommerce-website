"""Numbers for the admin dashboard."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.order import ORDER_STATUSES, RESTOCKING_STATUSES, Order
from app.models.order_item import OrderItem
from app.models.product import Product

CHART_DAYS = 14
LOW_STOCK = 3  # products with this many or fewer left are listed as "low stock"
LIST_SIZE = 5

# Confirmed but not delivered yet: the money is on its way (cash on delivery)
IN_PROGRESS_STATUSES = ("confirmed", "processing", "shipped")


def dashboard(db: Session) -> dict:
    def total_of(statuses) -> Decimal:
        return db.scalar(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.status.in_(statuses))
        )

    status_counts = dict.fromkeys(ORDER_STATUSES, 0) | dict(
        db.execute(select(Order.status, func.count()).group_by(Order.status)).all()
    )
    finished = status_counts["delivered"] + status_counts["returned"]
    average = db.scalar(select(func.avg(Order.total_amount)).where(Order.status == "delivered"))

    # Orders placed per day in the shop's time zone, including days with none
    zone = get_settings().shop_timezone
    today = datetime.now(ZoneInfo(zone)).date()
    days = [today - timedelta(days=n) for n in range(CHART_DAYS - 1, -1, -1)]
    local_day = func.date(func.timezone(zone, Order.created_at))
    placed = dict(
        db.execute(select(local_day, func.count()).where(local_day >= days[0]).group_by(local_day)).all()
    )

    # Stock is taken when an order is placed, so every order that wasn't cancelled
    # or returned counts as sold
    sold = func.sum(OrderItem.quantity).label("sold")
    top_products = db.execute(
        select(Product.id, Product.name, Product.image_url, sold)
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status.not_in(RESTOCKING_STATUSES))
        .group_by(Product.id)
        .order_by(sold.desc(), Product.id)
        .limit(LIST_SIZE)
    ).all()
    low_stock = db.scalars(
        select(Product)
        .where(Product.is_available, Product.stock_quantity <= LOW_STOCK)
        .order_by(Product.stock_quantity, Product.id)
    ).all()
    recent = db.scalars(select(Order).order_by(Order.created_at.desc(), Order.id).limit(LIST_SIZE)).all()

    return {
        # Cash on delivery: money is in hand only once an order is delivered
        "revenue": total_of(["delivered"]),
        "awaiting_payment": total_of(IN_PROGRESS_STATUSES),
        "average_order": round(average) if average is not None else Decimal(0),
        "return_rate": status_counts["returned"] / finished if finished else None,
        "customers": db.scalar(select(func.count(func.distinct(Order.customer_phone)))),
        "status_counts": status_counts,
        "orders_per_day": [{"date": day, "orders": placed.get(day, 0)} for day in days],
        "top_products": [
            {"id": id, "name": name, "image": image, "sold": count} for id, name, image, count in top_products
        ],
        "low_stock": [
            {"id": p.id, "name": p.name, "image": p.image_url, "stock": p.stock_quantity} for p in low_stock
        ],
        "recent_orders": [
            {"id": o.id, "order_number": o.order_number, "full_name": o.customer_name,
             "total": o.total_amount, "status": o.status, "created_at": o.created_at}
            for o in recent
        ],
    }
