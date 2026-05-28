"""Insighta SBI Tool — SBI証券パーサープラグイン。"""


def register(cli) -> None:
    """SBIコマンドをCLIに登録する。"""
    from insighta_sbi.commands import parse, verify

    cli.add_command(parse)
    cli.add_command(verify)
