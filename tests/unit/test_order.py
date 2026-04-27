"""Testes unitários para modelos de Order e PositionSizing."""

from decimal import Decimal

from packages.core.models.enums import OrderSide, OrderStatus, OrderType
from packages.core.models.order import Order, OrderOCO, PositionSizing


class TestOrder:
    def test_default_order(self):
        order = Order()
        assert order.status == OrderStatus.PENDING
        assert order.is_active is True
        assert order.is_closed is False

    def test_filled_order(self):
        order = Order(status=OrderStatus.FILLED)
        assert order.is_active is False
        assert order.is_closed is True

    def test_cancelled_order(self):
        order = Order(status=OrderStatus.CANCELLED)
        assert order.is_active is False
        assert order.is_closed is True

    def test_to_dict(self):
        order = Order(
            symbol="XAU/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            price=Decimal("2650.00"),
        )
        d = order.to_dict()
        assert d["symbol"] == "XAU/USD"
        assert d["side"] == "BUY"
        assert d["quantity"] == "0.1"


class TestOrderOCO:
    def test_risk_reward(self):
        entry = Order(price=Decimal("2650.00"), side=OrderSide.BUY)
        sl = Order(price=Decimal("2645.00"), side=OrderSide.SELL)
        tp = Order(price=Decimal("2657.50"), side=OrderSide.SELL)
        oco = OrderOCO(entry_order=entry, stop_loss_order=sl, take_profit_order=tp)

        assert oco.risk == Decimal("5.00")
        assert oco.reward == Decimal("7.50")
        assert oco.risk_reward_ratio == 1.5

    def test_zero_risk(self):
        entry = Order(price=Decimal("2650.00"))
        sl = Order(price=Decimal("2650.00"))
        tp = Order(price=Decimal("2660.00"))
        oco = OrderOCO(entry_order=entry, stop_loss_order=sl, take_profit_order=tp)

        assert oco.risk_reward_ratio == 0.0


class TestPositionSizing:
    def test_standard_sizing(self):
        sizing = PositionSizing(
            capital=Decimal("100000"),
            risk_percent=Decimal("0.01"),     # 1%
            entry_price=Decimal("2650.00"),
            stop_loss_price=Decimal("2645.00"),
        )
        # risk_amount = 1000, stop_distance = 5, position = 200
        assert sizing.risk_amount == Decimal("1000")
        assert sizing.stop_distance == Decimal("5.00")
        assert sizing.position_size == Decimal("200")

    def test_conservative_sizing(self):
        sizing = PositionSizing(
            capital=Decimal("50000"),
            risk_percent=Decimal("0.005"),     # 0.5%
            entry_price=Decimal("2650.00"),
            stop_loss_price=Decimal("2640.00"),
        )
        # risk_amount = 250, stop_distance = 10, position = 25
        assert sizing.risk_amount == Decimal("250.0")
        assert sizing.stop_distance == Decimal("10.00")
        assert sizing.position_size == Decimal("25.0")

    def test_zero_stop_distance(self):
        sizing = PositionSizing(
            capital=Decimal("100000"),
            risk_percent=Decimal("0.01"),
            entry_price=Decimal("2650.00"),
            stop_loss_price=Decimal("2650.00"),
        )
        assert sizing.position_size == Decimal("0")

    def test_to_dict(self):
        sizing = PositionSizing(
            capital=Decimal("100000"),
            risk_percent=Decimal("0.01"),
            entry_price=Decimal("2650.00"),
            stop_loss_price=Decimal("2645.00"),
        )
        d = sizing.to_dict()
        assert d["capital"] == "100000"
        assert d["position_size"] == "200"
