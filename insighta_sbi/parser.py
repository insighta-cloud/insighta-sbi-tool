"""SBI証券 HTML/CSVパーサー"""

import csv
import glob
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from bs4 import BeautifulSoup
from insighta_sdk import Deposit, Dirs, Holding, Trade

JST = timezone(timedelta(hours=9))

EXCHANGE_CURRENCY = {
    "NYSE": "USD", "NASDAQ": "USD", "NYSE Arca": "USD", "NYSE American": "USD",
    "KOSPI": "KRW", "KOSDAQ": "KRW",
    "TSE": "JPY",
}


def _to_jst_iso(dt_str: str) -> str:
    if not dt_str:
        return ""
    for fmt in ("%Y/%m/%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(dt_str, fmt).replace(tzinfo=JST).isoformat()
        except ValueError:
            continue
    return dt_str


def _to_decimal(val: str) -> Decimal:
    if not val or val == "-":
        return Decimal("0")
    return Decimal(val.replace(",", ""))


def _text(el, selector: str) -> str:
    found = el.select_one(selector)
    return found.text.strip() if found else ""


def _attr(el, selector: str, attr: str) -> str:
    found = el.select_one(selector)
    return found[attr] if found else ""


def _label_text(el) -> str:
    label = el.select_one("label") if el else None
    if not label:
        return ""
    return label.text.strip().replace(" USD", "").replace(" JPY", "")


# ---------------------------------------------------------------------------
# SBI deposit parsers
# ---------------------------------------------------------------------------

def _parse_sbi_transfer(filepath: str) -> list[Deposit]:
    """SBI証券 入出金振替操作履歴CSV (UTF-8)."""
    deposits: list[Deposit] = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "受付日時" in line and "状態" in line:
            header_idx = i
            break
    if header_idx is None:
        return deposits
    data_text = "\n".join(lines[header_idx:])
    for row in csv.DictReader(data_text.splitlines()):
        status = row.get("状態", "").strip()
        if status not in ("完了", "確定"):
            continue
        dt_raw = row.get("受付日時", "").strip()
        kubun = row.get("区分", "").strip()
        in_amt = row.get("入金指示金額", "-").strip()
        out_amt = row.get("出金指示金額", "-").strip()
        if kubun == "入金" and in_amt != "-":
            amount = Decimal(in_amt.replace(",", ""))
        elif kubun == "出金" and out_amt != "-":
            amount = -Decimal(out_amt.replace(",", ""))
        else:
            continue
        deposits.append(Deposit(dt=_to_jst_iso(dt_raw), amount=amount, cur="JPY", type="budget"))
    return deposits


def _parse_sbi_distribution(filepath: str) -> list[Deposit]:
    """SBI証券 配当金CSV (Shift_JIS)."""
    deposits: list[Deposit] = []
    with open(filepath, "r", encoding="shift_jis") as f:
        content = f.read()
    lines = content.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "受渡日" in line and "銘柄名" in line:
            header_idx = i
            break
    if header_idx is None:
        return deposits
    data_text = "\n".join(lines[header_idx:])
    for row in csv.DictReader(data_text.splitlines()):
        product = row.get("商品", "").strip()
        if "米国株式" in product:
            continue
        dt_raw = row.get("受渡日", "").strip()
        name = row.get("銘柄名", "").strip()
        amt_str = row.get("受取額(税引後・円)", "").strip().replace("\n", "").replace(",", "")
        if not dt_raw or not amt_str:
            continue
        try:
            amount = Decimal(amt_str)
        except Exception:
            continue
        ticker = name.split()[-1] if name else ""
        deposits.append(Deposit(dt=_to_jst_iso(dt_raw), amount=amount, cur="JPY", type="dividend", ticker=ticker))
    return deposits


def _parse_sbi_exchange(filepath: str) -> list[Deposit]:
    """SBI証券 為替取引注文履歴CSV (Shift_JIS)."""
    deposits: list[Deposit] = []
    with open(filepath, "rb") as f:
        raw = f.read()
    content = raw.decode("shift_jis", errors="ignore")
    lines = content.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "口座区分" in line and "約定レート" in line:
            header_idx = i
            break
    if header_idx is None:
        return deposits
    data_text = "\n".join(lines[header_idx:])
    CURRENCY_MAP = {"米ドル": "USD", "ユーロ": "EUR", "英ポンド": "GBP", "豪ドル": "AUD"}
    for row in csv.DictReader(data_text.splitlines()):
        status = row.get("注文状況", "").strip()
        if status != "約定済":
            continue
        dt_raw = row.get("約定日時", "").strip().replace("\n", "")
        qty_str = row.get("数量", "0").strip().replace(",", "")
        jpy_str = row.get("受渡金額", "0").strip().replace(",", "")
        rate_str = row.get("約定レート", "").strip()
        currency_ja = row.get("通貨", "").strip()
        order_type = row.get("注文種別", "").strip()
        foreign_cur = CURRENCY_MAP.get(currency_ja, currency_ja)
        try:
            qty = Decimal(qty_str)
            jpy_amount = Decimal(jpy_str)
            rate = Decimal(rate_str) if rate_str else None
        except Exception:
            continue
        dt_iso = _to_jst_iso(dt_raw)
        if order_type == "買付":
            deposits.append(Deposit(dt=dt_iso, amount=-jpy_amount, cur="JPY", type="budget", rate=rate))
            deposits.append(Deposit(dt=dt_iso, amount=qty, cur=foreign_cur, type="budget", rate=rate))
        elif order_type == "売付":
            deposits.append(Deposit(dt=dt_iso, amount=-qty, cur=foreign_cur, type="budget", rate=rate))
            deposits.append(Deposit(dt=dt_iso, amount=jpy_amount, cur="JPY", type="budget", rate=rate))
    return deposits


def _parse_sbi_gaika_nyushukkin(filepath: str) -> list[Deposit]:
    """SBI証券 外貨入出金明細CSV."""
    deposits: list[Deposit] = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        content = f.read()
    lines = content.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "入出金日" in line and "区分" in line and "入金額" in line:
            header_idx = i
            break
    if header_idx is None:
        return deposits
    data_text = "\n".join(lines[header_idx:])
    for row in csv.DictReader(data_text.splitlines()):
        kubun = row.get("区分", "").strip()
        tekiyou = row.get("摘要", "").strip()
        dt_raw = row.get("入出金日", "").strip()
        if not dt_raw:
            continue
        if kubun in ("分配金", "配当金"):
            amount_str = row.get("入金額", "0").strip().replace(",", "")
            if not amount_str or amount_str == "0":
                continue
            try:
                amount = Decimal(amount_str)
            except Exception:
                continue
            ticker = tekiyou.split()[0] if tekiyou.split() else ""
            deposits.append(Deposit(dt=_to_jst_iso(dt_raw), amount=amount, cur="USD", type="dividend", ticker=ticker))
        elif kubun == "-" and ("外貨出金" in tekiyou or "外貨入金" in tekiyou):
            out_str = row.get("出金額", "0").strip().replace(",", "")
            in_str = row.get("入金額", "0").strip().replace(",", "")
            try:
                out_amt = Decimal(out_str) if out_str and out_str != "0" else Decimal(0)
                in_amt = Decimal(in_str) if in_str and in_str != "0" else Decimal(0)
            except Exception:
                continue
            amount = in_amt - out_amt
            if amount == 0:
                continue
            deposits.append(Deposit(dt=_to_jst_iso(dt_raw), amount=amount, cur="USD", type="budget"))
    return deposits


# ---------------------------------------------------------------------------
# HTML parsers
# ---------------------------------------------------------------------------

def parse_history_html(filename: str) -> tuple[list[Trade], list[str]]:
    """注文履歴HTMLをパースし、約定済み取引リストとスキップ理由を返す。"""
    with open(filename, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    trades, skipped = [], []
    for row in soup.select("li.table-row"):
        status = _text(row, ".sticker")
        dt_raw = _text(row, '[data-label="国内注文日時："]')
        ticker = _attr(row, "[data-security-code]", "data-security-code")
        trade_type = _text(row, '[data-label="取引"]')
        is_buy = "買" in trade_type
        acct_raw = _text(row, '[data-label="預り"]')
        acct = "TT" if acct_raw == "特定" else acct_raw
        qty_str = _text(row, '[data-label="数量(未約定数量)"] label')
        avg_str = _text(row, '[data-label="平均約定単価"] label')
        price_str = _text(row, '[data-label="現在値"] label')
        payment = _text(row, '[data-label="決済方法"]')
        cur = "USD" if payment == "外貨" else "JPY"
        qty_signed = qty_str if is_buy else f"-{qty_str}"

        if status != "完了":
            skipped.append(f"[{status}] {dt_raw} {ticker} {qty_signed}")
            continue
        if avg_str in ("-", ""):
            skipped.append(f"[avg無し] {dt_raw} {ticker} {qty_signed}")
            continue

        code_el = row.select_one("[data-security-code]")
        exchange = ""
        if code_el:
            p_el = code_el.select_one("p.md-font-xs")
            if p_el:
                exchange = p_el.text.replace(ticker, "").strip()
        base = EXCHANGE_CURRENCY.get(exchange, "USD")

        trades.append(Trade(
            dt=_to_jst_iso(dt_raw), ticker=ticker,
            qty=int(qty_signed), acct=acct,
            price=_to_decimal(price_str), avg=_to_decimal(avg_str),
            cur=cur, base=base,
        ))
    return trades, skipped


def parse_summary_html(filename: str) -> list[Holding]:
    """保有銘柄HTMLをパースし、銘柄リストを返す。"""
    with open(filename, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    holdings = []
    current_acct = ""
    for sec in soup.select("li.css-djjzqp"):
        header = sec.select_one("div.bb-light > .font-bold.font-sm") or \
                 sec.select_one(".font-bold.font-sm.p-x-1")
        if header:
            txt = header.text.strip()
            if "特定" in txt:
                current_acct = "TT"
            elif "NISA" in txt:
                current_acct = "NISA"
            continue
        if not current_acct:
            continue
        for el in sec.select("[data-security-code]"):
            ticker = el["data-security-code"]
            parent = el.find_parent("div", class_="p-half")
            if not parent:
                continue
            siblings = parent.find_next_siblings("div")
            vals = [_label_text(s) for s in siblings[:4]]
            if vals[0]:
                holdings.append(Holding(
                    ticker=ticker, acct=current_acct, qty=int(vals[0]),
                    cost=_to_decimal(vals[1]), price=_to_decimal(vals[2]), pnl=_to_decimal(vals[3]),
                ))
    return holdings


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
