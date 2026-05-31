"""SBI証券 HTML/CSVパーサー — insighta-sbi-parser アダプター.

後方互換性のため、既存のインターフェースを維持しつつ
insighta_sbi_parser に処理を委譲する。
"""

import csv
import glob
import os
from decimal import Decimal

import insighta_sbi_parser
from insighta_sbi_parser.html_parser import EXCHANGE_CURRENCY  # noqa: F401
from insighta_sbi_parser.utils import to_jst_iso as _to_jst_iso
from insighta_sdk import Deposit, Dirs, Holding, Trade

# Re-export for backward compat
EXCHANGE_CURRENCY = EXCHANGE_CURRENCY


def _to_decimal(val: str) -> Decimal:
    return insighta_sbi_parser.utils.to_decimal(val)


# ---------------------------------------------------------------------------
# HTML パーサー (委譲)
# ---------------------------------------------------------------------------

def parse_history_html(filename: str) -> tuple[list[Trade], list[str]]:
    """注文履歴HTMLをパースし、約定済み取引リストとスキップ理由を返す。"""
    raw_trades, skipped = insighta_sbi_parser.parse_history_html(filename)
    trades = [Trade(dt=t.dt, ticker=t.ticker, qty=t.qty, acct=t.acct,
                    price=t.price, avg=t.avg, cur=t.cur, base=t.base)
              for t in raw_trades]
    return trades, skipped


def parse_summary_html(filename: str) -> list[Holding]:
    """保有銘柄HTMLをパースし、銘柄リストを返す。"""
    raw = insighta_sbi_parser.parse_summary_html(filename)
    return [Holding(ticker=h.ticker, acct=h.acct, qty=h.qty,
                    cost=h.cost, price=h.price, pnl=h.pnl)
            for h in raw]


# ---------------------------------------------------------------------------
# 入出金パーサー (委譲)
# ---------------------------------------------------------------------------

def _parse_sbi_transfer(filepath: str) -> list[Deposit]:
    """SBI証券 入出金振替操作履歴CSV (UTF-8)."""
    raw = insighta_sbi_parser.parse_transfer(filepath)
    return [Deposit(dt=d.dt, amount=d.amount, cur=d.cur, type=d.type,
                    ticker=d.ticker, rate=d.rate) for d in raw]


def _parse_sbi_distribution(filepath: str) -> list[Deposit]:
    """SBI証券 配当金CSV (Shift_JIS)."""
    raw = insighta_sbi_parser.parse_distribution(filepath)
    return [Deposit(dt=d.dt, amount=d.amount, cur=d.cur, type=d.type,
                    ticker=d.ticker, rate=d.rate) for d in raw]


def _parse_sbi_exchange(filepath: str) -> list[Deposit]:
    """SBI証券 為替取引注文履歴CSV (Shift_JIS)."""
    raw = insighta_sbi_parser.parse_exchange(filepath)
    return [Deposit(dt=d.dt, amount=d.amount, cur=d.cur, type=d.type,
                    ticker=d.ticker, rate=d.rate) for d in raw]


def _parse_sbi_gaika_nyushukkin(filepath: str) -> list[Deposit]:
    """SBI証券 外貨入出金明細CSV."""
    raw = insighta_sbi_parser.parse_gaika_nyushukkin(filepath)
    return [Deposit(dt=d.dt, amount=d.amount, cur=d.cur, type=d.type,
                    ticker=d.ticker, rate=d.rate) for d in raw]


# ---------------------------------------------------------------------------
# ユーティリティ (既存インターフェース維持)
# ---------------------------------------------------------------------------

def find_htmls(prefix: str, dirs: Dirs) -> list[str]:
    """input/内の指定プレフィックスのHTMLファイルを検索。"""
    dir_map = {"history": dirs.history, "summary": dirs.summary}
    d = dir_map.get(prefix, os.path.join(dirs.input, prefix))
    files = sorted(glob.glob(f"{d}/*.html"))
    if not files:
        raise FileNotFoundError(f"{d}/ に *.html が見つかりません")
    return files


def load_deposits(dirs: Dirs) -> list[Deposit]:
    """input/deposit/*.csv を自動判別して読み込む。"""
    deposits: list[Deposit] = []
    for fname in sorted(glob.glob(f"{dirs.deposit}/*.csv")):
        try:
            with open(fname, "r", encoding="utf-8-sig") as f:
                if f.readline().strip() == "insighta-deposit":
                    deposits.extend(_parse_plain_deposit(fname))
                    continue
        except Exception:
            pass
        try:
            with open(fname, "r", encoding="utf-8-sig") as f:
                head = f.read(512)
            if "外貨入出金明細" in head:
                deposits.extend(_parse_sbi_gaika_nyushukkin(fname))
                continue
        except Exception:
            pass
        try:
            with open(fname, "r", encoding="utf-8") as f:
                head = f.read(512)
            if "入出金振替操作履歴" in head or ("受付日時" in head and "状態" in head):
                deposits.extend(_parse_sbi_transfer(fname))
                continue
        except Exception:
            pass
        try:
            with open(fname, "rb") as f:
                raw = f.read(512)
            text = raw.decode("shift_jis", errors="ignore")
            if "受渡日" in text and "銘柄名" in text:
                deposits.extend(_parse_sbi_distribution(fname))
                continue
        except Exception:
            pass
    for fname in sorted(glob.glob(f"{dirs.exchange}/*.csv")):
        try:
            with open(fname, "rb") as f:
                raw = f.read(512)
            text = raw.decode("shift_jis", errors="ignore")
            if "為替取引注文履歴" in text or ("口座区分" in text and "約定レート" in text):
                deposits.extend(_parse_sbi_exchange(fname))
        except Exception:
            pass
    return deposits


def _parse_plain_deposit(filepath: str) -> list[Deposit]:
    with open(filepath, "r", encoding="utf-8-sig") as f:
        f.readline()
        deposits: list[Deposit] = []
        for row in csv.DictReader(f):
            amt = Decimal(row["amount"].replace(",", ""))
            rate = Decimal(row["rate"].replace(",", "")) if row.get("rate", "").strip() else None
            deposits.append(Deposit(
                dt=_to_jst_iso(row["dt"]), amount=amt, cur=row["cur"].strip(),
                type=row["type"].strip(), ticker=row.get("ticker", "").strip(), rate=rate,
            ))
    return deposits


def load_csv_rows(dirs: Dirs) -> list[dict]:
    """input/seed/*.csv + input/manual/seed.csv + output/history.csv を読み込む。"""
    rows = []
    for pattern in [f"{dirs.seed}/*.csv", f"{dirs.manual}/seed.csv", dirs.history_csv]:
        for fname in glob.glob(pattern):
            with open(fname, "r", encoding="utf-8") as f:
                rows.extend(csv.DictReader(f))
    return rows


def aggregate_holdings(rows: list[dict]) -> dict[tuple[str, str], int]:
    """CSV行からティッカー×口座ごとの保有数を集計。"""
    holdings: dict[tuple[str, str], int] = {}
    for r in rows:
        key = (r["ticker"], r["acct"])
        holdings[key] = holdings.get(key, 0) + int(r["qty"])
    return {k: v for k, v in holdings.items() if v != 0}
