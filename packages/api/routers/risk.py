"""Risk monitoring endpoints — exposicao, P&L e alertas."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from packages.api.dependencies import app_state

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/summary")
async def risk_summary():
    """Retorna resumo de risco, exposicao e P&L."""
    pt = app_state.paper_trader
    if not pt:
        return {
            "status": "inactive",
            "equity": 0,
            "initial_capital": 10000,
            "capital_at_risk": 0,
            "capital_at_risk_pct": 0,
            "daily_pnl": 0,
            "weekly_pnl": 0,
            "monthly_pnl": 0,
            "current_drawdown_pct": 0,
            "max_drawdown_pct": 0,
            "open_positions": [],
            "risk_alerts": [],
            "metrics": {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "sharpe_ratio": 0,
                "recovery_factor": 0,
                "expectancy": 0,
                "avg_r_multiple": 0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
            },
            "equity_curve": [10000],
        }

    state = pt.state
    m = pt.metrics
    config = pt._config

    capital_at_risk = 0.0
    positions = []
    for t in state.open_trades:
        risk = abs(float(t.entry_price - t.stop_loss)) * float(t.position_size)
        capital_at_risk += risk
        positions.append({
            "direction": t.direction.value,
            "pattern": t.pattern_type.value,
            "entry_price": str(t.entry_price),
            "stop_loss": str(t.stop_loss),
            "take_profit": str(t.take_profit),
            "risk_amount": round(risk, 2),
            "confluence": round(t.confluence_score, 4),
            "entry_time": t.entry_time.isoformat(),
        })

    now = datetime.utcnow()
    daily_pnl = sum(
        float(t.net_pnl)
        for t in state.closed_trades
        if t.exit_time and (now - t.exit_time).days < 1
    )
    weekly_pnl = sum(
        float(t.net_pnl)
        for t in state.closed_trades
        if t.exit_time and (now - t.exit_time).days < 7
    )
    monthly_pnl = sum(
        float(t.net_pnl)
        for t in state.closed_trades
        if t.exit_time and (now - t.exit_time).days < 30
    )

    equity = state.equity
    peak = config.initial_capital
    for t in state.closed_trades:
        peak = max(peak, peak + float(t.net_pnl))
    current_dd = (peak - equity) / peak if peak > 0 else 0

    alerts = []
    risk_pct = capital_at_risk / equity * 100 if equity > 0 else 0
    if risk_pct > 5:
        alerts.append({
            "level": "HIGH",
            "message": f"Exposicao de {risk_pct:.1f}% do capital em risco",
        })
    if current_dd > 0.02:
        alerts.append({
            "level": "WARNING",
            "message": f"Drawdown atual de {current_dd * 100:.1f}%",
        })
    if len(state.open_trades) >= config.max_concurrent_trades:
        alerts.append({
            "level": "INFO",
            "message": "Limite de trades simultaneos atingido",
        })
    if m.max_drawdown_pct > 0.03:
        alerts.append({
            "level": "HIGH",
            "message": f"Max drawdown {m.max_drawdown_pct * 100:.1f}% excede limite de 3%",
        })

    return {
        "status": "active" if state.is_running else "stopped",
        "equity": round(equity, 2),
        "initial_capital": config.initial_capital,
        "capital_at_risk": round(capital_at_risk, 2),
        "capital_at_risk_pct": round(risk_pct, 2),
        "daily_pnl": round(daily_pnl, 2),
        "weekly_pnl": round(weekly_pnl, 2),
        "monthly_pnl": round(monthly_pnl, 2),
        "current_drawdown_pct": round(current_dd * 100, 2),
        "max_drawdown_pct": round(m.max_drawdown_pct * 100, 2),
        "open_positions": positions,
        "risk_alerts": alerts,
        "metrics": {
            "total_trades": m.total_trades,
            "win_rate": round(m.win_rate * 100, 1),
            "profit_factor": round(m.profit_factor, 2),
            "sharpe_ratio": round(m.sharpe_ratio, 2),
            "recovery_factor": round(m.recovery_factor, 2),
            "expectancy": round(m.expectancy, 2),
            "avg_r_multiple": round(m.avg_r_multiple, 2),
            "max_consecutive_wins": m.max_consecutive_wins,
            "max_consecutive_losses": m.max_consecutive_losses,
        },
        "equity_curve": m.equity_curve,
    }
