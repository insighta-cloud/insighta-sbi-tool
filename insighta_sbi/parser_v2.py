"""SBI証券 input/sbi/ 自動認識パーサー (v2) — insighta-sbi-parser アダプター."""

import os
from dataclasses import dataclass, field

import insighta_sbi_parser
from insighta_sdk import Deposit, Dirs, Holding, Trade


@dataclass
class ParseResult:
    trades: list[Trade] = field(default_factory=list)
    holdings: list[Holding] = field(default_factory=list)
    deposits: list[Deposit] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def merge(self, other: "ParseResult"):
        self.trades.extend(other.trades)
        self.holdings.extend(other.holdings)
        self.deposits.extend(other.deposits)
        self.skipped.extend(other.skipped)
        self.warnings.extend(other.warnings)


def _convert_result(src: insighta_sbi_parser.ParseResult) -> ParseResult:
    """insighta_sbi_parser の型を insighta_sdk の型に変換."""
    return ParseResult(
        trades=[Trade(dt=t.dt, ticker=t.ticker, qty=t.qty, acct=t.acct,
                      price=t.price, avg=t.avg, cur=t.cur, base=t.base)
                for t in src.trades],
        holdings=[Holding(ticker=h.ticker, acct=h.acct, qty=h.qty,
                          cost=h.cost, price=h.price, pnl=h.pnl)
                  for h in src.holdings],
        deposits=[Deposit(dt=d.dt, amount=d.amount, cur=d.cur, type=d.type,
                          ticker=d.ticker, rate=d.rate)
                  for d in src.deposits],
        skipped=src.skipped,
        warnings=src.warnings,
    )


# Re-export for backward compat
classify = insighta_sbi_parser.classify


def process_sbi_dir(sbi_dir: str, cache_dir: str | None = None, rate_file: str = "") -> ParseResult:
    """input/sbi/ ディレクトリ内の全ファイルを自動分類・パース。"""
    src = insighta_sbi_parser.process_sbi_dir(sbi_dir, rate_file=rate_file)
    result = _convert_result(src)

    if cache_dir:
        _save_cache(result, cache_dir)
    return result


def _save_cache(result: ParseResult, cache_dir: str):
    import pandas as pd
    os.makedirs(cache_dir, exist_ok=True)
    if result.trades:
        rows = [{"dt": t.dt, "ticker": t.ticker, "qty": t.qty, "acct": t.acct,
                 "price": str(t.price), "avg": str(t.avg), "cur": t.cur, "base": t.base}
                for t in result.trades]
        pd.DataFrame(rows).to_csv(os.path.join(cache_dir, "trades.csv"), index=False, encoding="utf-8")
    if result.holdings:
        rows = [{"ticker": h.ticker, "acct": h.acct, "qty": h.qty,
                 "cost": str(h.cost), "price": str(h.price), "pnl": str(h.pnl)}
                for h in result.holdings]
        pd.DataFrame(rows).to_csv(os.path.join(cache_dir, "holdings.csv"), index=False, encoding="utf-8")
    if result.deposits:
        rows = [{"dt": d.dt, "type": d.type, "amount": str(d.amount), "cur": d.cur,
                 "ticker": d.ticker, "rate": str(d.rate) if d.rate is not None else ""}
                for d in result.deposits]
        pd.DataFrame(rows).to_csv(os.path.join(cache_dir, "deposits.csv"), index=False, encoding="utf-8")
    if result.warnings:
        with open(os.path.join(cache_dir, "warnings.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(result.warnings))


def load_deposits_for_prepare(dirs: Dirs) -> list[Deposit]:
    """insighta_cli.deposit_loader プラグインのエントリーポイント。"""
    sbi_dir = os.path.join(dirs.input, "sbi") if hasattr(dirs, 'input') else ""
    if not sbi_dir or not os.path.isdir(sbi_dir):
        return []
    rate_file = ""
    for candidate in [dirs.rate_csv, os.path.join(dirs.manual, "rate.csv")]:
        if os.path.exists(candidate):
            rate_file = candidate
            break
    result = process_sbi_dir(sbi_dir, rate_file=rate_file)
    return result.deposits
