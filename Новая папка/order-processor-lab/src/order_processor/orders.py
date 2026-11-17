"""Обработка и сохранение заказов."""

import logging
import sqlite3
from typing import Any

from order_processor.errors import OrderValidationError

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = (
    "CREATE TABLE IF NOT EXISTS orders "
    "(order_id TEXT PRIMARY KEY, email TEXT, total REAL)"
)


def _validate_discount(discount: float) -> None:
    if not 0 <= discount <= 100:
        raise OrderValidationError(f"discount must be in [0, 100], got {discount}")


def _validate_item(item: dict[str, Any]) -> None:
    if "qty" not in item or "price" not in item:
        raise OrderValidationError("item must contain 'qty' and 'price'")
    if item["qty"] <= 0:
        raise OrderValidationError(f"qty must be positive, got {item['qty']}")
    if item["price"] < 0:
        raise OrderValidationError(f"price must be non-negative, got {item['price']}")


def _validate_email(email: str | None) -> None:
    if email is not None and "@" not in email:
        raise OrderValidationError(f"invalid email: {email!r}")


def _validate_order(order: dict[str, Any] | None) -> None:
    if order is None:
        raise OrderValidationError("order is required")
    if not order.get("order_id"):
        raise OrderValidationError("order_id is required")
    if not order.get("items"):
        raise OrderValidationError("items must be a non-empty list")
    _validate_email(order.get("email"))


def _calculate_total(items: list[dict[str, Any]], discount: float) -> float:
    if not items:
        raise OrderValidationError("items must be a non-empty list")
    _validate_discount(discount)
    for item in items:
        _validate_item(item)
    subtotal = sum(item["qty"] * item["price"] for item in items)
    return subtotal - subtotal * discount / 100


def _save_order(db_path: str, order_id: str, email: str | None, total: float) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(_CREATE_TABLE_SQL)
        conn.execute(
            "INSERT OR REPLACE INTO orders VALUES (?, ?, ?)",
            (order_id, email, total),
        )


def process_order(order: dict[str, Any] | None, db_path: str) -> float:
    """Валидирует заказ, считает итог и сохраняет его в БД. Возвращает итоговую сумму."""
    _validate_order(order)
    assert order is not None  # noqa: S101  (сужение типа после валидации)
    total = _calculate_total(order["items"], order.get("discount", 0))
    _save_order(db_path, order["order_id"], order.get("email"), total)
    logger.info("Order %s saved, total=%s", order["order_id"], total)
    return total


def preview_total(items: list[dict[str, Any]], discount: float = 0) -> float:
    """Считает итог без сохранения."""
    return _calculate_total(items, discount)
