"""Insighta SBI Tool — SBI証券パーサープラグイン。"""

from insighta_sbi.commands import _run_verify
from insighta_sbi.commands import parse as _parse_click
from insighta_sbi.commands import verify as _verify_click


def register(cli) -> None:
    """レガシー: SBIコマンドをCLIに直接登録する。"""
    cli.add_command(_parse_click)
    cli.add_command(_verify_click)


def parse_command(obj, rate="", rate_file="") -> None:
    """CLIルーターから呼び出されるパースエントリーポイント。"""
    from click import Context

    ctx = Context(_parse_click)
    ctx.obj = obj
    ctx.invoke(_parse_click, rate=rate, rate_file=rate_file)


def verify_command(obj) -> None:
    """CLIルーターから呼び出される検証エントリーポイント。"""
    _run_verify(obj["dirs"])
