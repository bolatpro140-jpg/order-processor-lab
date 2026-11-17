import sqlite3
from pathlib import Path

import pytest

from order_processor.errors import OrderValidationError
from order_processor.orders import preview_total, process_order

VALID = {
    "order_id": "A-1",
    "email": "user@example.com",
    "items": [{"qty": 2, "price": 10.0}, {"qty": 1, "price": 5.0}],
    "discount": 10,
}


def _rows(db: Path) -> list[tuple]:
    with sqlite3.connect(db) as conn:
        return conn.execute("SELECT order_id, email, total FROM orders").fetchall()


def test_valid_order_saved(tmp_path: Path) -> None:
    db = tmp_path / "o.db"
    assert process_order(VALID, str(db)) == pytest.approx(22.5)
    assert _rows(db) == [("A-1", "user@example.com", 22.5)]


def test_no_print_in_business_logic(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    process_order(VALID, str(tmp_path / "o.db"))
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "order",
    [
        None,
        {"items": [{"qty": 1, "price": 1.0}]},
        {"order_id": "X"},
        {"order_id": "X", "items": []},
        {"order_id": "", "items": [{"qty": 1, "price": 1.0}]},
        {"order_id": "X", "items": [{"qty": 0, "price": 1.0}]},
        {"order_id": "X", "items": [{"qty": -1, "price": 1.0}]},
        {"order_id": "X", "items": [{"qty": 1, "price": -1.0}]},
        {"order_id": "X", "items": [{"qty": 1}]},
        {"order_id": "X", "items": [{"qty": 1, "price": 1.0}], "discount": -1},
        {"order_id": "X", "items": [{"qty": 1, "price": 1.0}], "discount": 101},
        {"order_id": "X", "items": [{"qty": 1, "price": 1.0}], "email": "no-at-sign"},
    ],
)
def test_invalid_order_raises_and_not_saved(order: dict | None, tmp_path: Path) -> None:
    db = tmp_path / "o.db"
    with pytest.raises(OrderValidationError):
        process_order(order, str(db))  # type: ignore[arg-type]
    assert not db.exists() or _rows(db) == []


@pytest.mark.parametrize(
    ("items", "discount", "expected"),
    [
        ([{"qty": 1, "price": 100.0}], 0, 100.0),
        ([{"qty": 2, "price": 50.0}], 50, 50.0),
        ([{"qty": 1, "price": 100.0}], 100, 0.0),
    ],
)
def test_preview_total_boundaries(items: list[dict], discount: float, expected: float) -> None:
    assert preview_total(items, discount) == pytest.approx(expected)


@pytest.mark.parametrize("discount", [-0.01, 100.01])
def test_preview_total_bad_discount(discount: float) -> None:
    with pytest.raises(OrderValidationError):
        preview_total([{"qty": 1, "price": 1.0}], discount)


def test_preview_total_empty_items() -> None:
    with pytest.raises(OrderValidationError):
        preview_total([], 0)
