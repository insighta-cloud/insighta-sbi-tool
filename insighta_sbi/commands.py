"""SBI証券 パース・検証 CLIコマンド。"""

import csv
import os

import rich_click as click
from insighta_sdk import Dirs, load_rate_file, lookup_rate
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.command()
@click.option("--rate", default="", help="Fixed exchange rate (e.g. 155.12)")
@click.option("--rate-file", default="", help="Period-based exchange rate CSV")
@click.pass_obj
def parse(obj, rate, rate_file) -> None:
    """SBI証券の取引履歴HTMLをパースしてCSVを生成する。"""
    from .parser_v2 import process_sbi_dir

    dirs: Dirs = obj["dirs"]
    dirs.ensure_output()

    sbi_dir = os.path.join(dirs.input, "sbi")

    if not rate_file:
        for candidate in [dirs.rate_csv, os.path.join(dirs.manual, "rate.csv")]:
            if os.path.exists(candidate):
                rate_file = candidate
                break

    result = process_sbi_dir(
        sbi_dir, rate_file=rate_file, cache_dir=os.path.join(dirs._base or ".", ".cache"),
    )

    rates = load_rate_file(rate_file) if rate_file else []

    # history.csv
    out = dirs.history_csv
    deduped = sorted(result.trades, key=lambda t: t.dt, reverse=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dt", "ticker", "qty", "acct", "price", "avg", "cur", "base", "rate"])
        for t in deduped:
            r = lookup_rate(rates, t.dt, t.cur, t.base) if rates else (rate if t.cur != t.base else "")
            w.writerow([t.dt, t.ticker, t.qty, t.acct, t.price, t.avg, t.cur, t.base, r or ""])

    # 入出金
    os.makedirs(os.path.join(dirs.input, "deposit"), exist_ok=True)
    dep_out = os.path.join(dirs.input, "deposit", "_auto_deposits.csv")
    if result.deposits:
        with open(dep_out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["dt", "amount", "cur", "type", "ticker", "rate"])
            for d in result.deposits:
                w.writerow([d.dt, str(d.amount), d.cur, d.type, d.ticker, str(d.rate) if d.rate else ""])

    # サマリー表示
    table = Table(title="Parse Result")
    table.add_column("")
    table.add_column("", justify="right")
    table.add_row("Trades", str(len(result.trades)))
    table.add_row("Holdings", str(len(result.holdings)))
    table.add_row("Deposits", str(len(result.deposits)))
    if result.skipped:
        table.add_row("Skipped", str(len(result.skipped)))
    if result.warnings:
        table.add_row("[yellow]Warnings[/yellow]", str(len(result.warnings)))
    console.print(table)
    console.print(f"[green]✅ {out}[/green]")

    if result.warnings:
        for w in result.warnings:
            console.print(f"  [yellow]⚠ {w}[/yellow]")


@click.command()
@click.pass_obj
def verify(obj) -> None:
    """CSV集計結果を実際のHTML保有銘柄と照合する。"""
    _run_verify(obj["dirs"])


def _run_verify(dirs: Dirs) -> bool:
    """CSV集計の保有数と実際のHTML保有数を比較する。

    Args:
        dirs: ワークスペースを指すDirsインスタンス。

    Returns:
        CSV集計が実際の保有数と一致する場合True。
    """

    from .parser import aggregate_holdings, load_csv_rows
    from .parser_v2 import process_sbi_dir

    rows = load_csv_rows(dirs)
    holdings = aggregate_holdings(rows)

    rate_file = ""
    for candidate in [dirs.rate_csv, os.path.join(dirs.manual, "rate.csv")]:
        if os.path.exists(candidate):
            rate_file = candidate
            break
    _v2_result = process_sbi_dir(os.path.join(dirs.input, "sbi"), rate_file=rate_file)

    # 移動平均取得単価の計算
    _avg_price: dict[str, float] = {}
    _hold_qty: dict[str, int] = {}
    sorted_rows = sorted(rows, key=lambda r: r.get("dt", ""))
    for r in sorted_rows:
        t, q, p = r["ticker"], int(r["qty"]), float(r.get("price") or 0)
        if q > 0 and p > 0:
            prev_qty = _hold_qty.get(t, 0)
            prev_avg = _avg_price.get(t, 0.0)
            _avg_price[t] = (prev_avg * prev_qty + p * q) / (prev_qty + q)
            _hold_qty[t] = prev_qty + q
        elif q < 0:
            _hold_qty[t] = _hold_qty.get(t, 0) + q
    csv_avg: dict[str, float] = {t: round(v, 2) for t, v in _avg_price.items() if _hold_qty.get(t, 0) > 0}

    by_acct: dict[str, list[tuple[str, int]]] = {}
    for (ticker, acct), qty in holdings.items():
        by_acct.setdefault(acct, []).append((ticker, qty))
    for acct in by_acct:
        by_acct[acct].sort()

    actual: dict[tuple[str, str], int] = {}
    prices: dict[str, dict] = {}
    for h in _v2_result.holdings:
        actual[(h.ticker, h.acct)] = h.qty
        prices[h.ticker] = {"cost": h.cost, "price": h.price, "pnl": h.pnl}

    for acct in sorted(by_acct):
        icon = "🟢" if acct == "NISA" else "🔵"
        table = Table(title=f"{icon} {acct}")
        table.add_column("Ticker")
        table.add_column("Qty", justify="right")
        table.add_column("Cost", justify="right")
        table.add_column("CSV Avg", justify="right")
        table.add_column("Price", justify="right")
        table.add_column("P&L", justify="right")
        table.add_column("Check", justify="center")
        for ticker, qty in by_acct[acct]:
            p = prices.get(ticker, {})
            a_qty = actual.get((ticker, acct))
            check = "[yellow]⚠[/yellow]" if a_qty is None else (
                "[green]✅[/green]" if a_qty == qty else "[red]❌[/red]")
            pnl = p.get("pnl", "-")
            pnl_style = "red" if pnl != "-" and pnl < 0 else "green"
            pnl_str = f"[{pnl_style}]{pnl}[/{pnl_style}]" if pnl != "-" else "-"
            ca = csv_avg.get(ticker)
            ca_str = str(ca) if ca is not None else "-"
            table.add_row(
                ticker, str(qty), str(p.get("cost", "-")),
                ca_str, str(p.get("price", "-")), pnl_str, check,
            )
        console.print(table)

    diffs = []
    for key in set(holdings) | set(actual):
        csv_qty, act_qty = holdings.get(key, 0), actual.get(key, 0)
        if csv_qty != act_qty:
            ticker, acct = key
            diffs.append((acct, ticker, csv_qty, act_qty, act_qty - csv_qty,
                          prices.get(ticker, {}).get("price", "-")))

    if diffs:
        table = Table(title="🔴 Differences (Actual - Aggregated)")
        table.add_column("Account")
        table.add_column("Ticker")
        table.add_column("Aggregated", justify="right")
        table.add_column("Actual", justify="right")
        table.add_column("Diff", justify="right")
        table.add_column("Price", justify="right")
        for acct, ticker, csv_q, act_q, diff, price in sorted(diffs):
            sign = f"+{diff}" if diff > 0 else str(diff)
            table.add_row(acct, ticker, str(csv_q), str(act_q), sign, str(price))
        console.print(table)
        return False

    console.print(Panel("[bold green]✅ Aggregation matches actual holdings[/bold green]"))
    return True
