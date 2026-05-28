"""Insighta SBI Tool - SBI Securities parser plugin."""


def register(cli) -> None:
    """Register SBI commands with the CLI."""
    from insighta_sbi.commands import parse, verify

    cli.add_command(parse)
    cli.add_command(verify)
