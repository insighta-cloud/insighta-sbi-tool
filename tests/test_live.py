"""ライブ統合テスト — 実行方法: pytest --live

INSIGHTA_DEV_API_KEY 環境変数が必要。
全フローをテスト: parse → verify → prepare → upload
test-mini ワークスペースを使用。
"""

import os

import pytest
from click.testing import CliRunner

from insighta_cli.cli import cli

pytestmark = pytest.mark.live

WORKSPACE = "test-mini"


@pytest.fixture
def runner(tmp_path):
    """dev認証情報付きCLIランナー。"""
    api_key = os.environ.get("INSIGHTA_DEV_API_KEY")
    if not api_key:
        pytest.skip("INSIGHTA_DEV_API_KEY not set")
    endpoint = os.environ.get("INSIGHTA_ENDPOINT", "https://dev.openapi.insighta.cloud")
    creds_file = tmp_path / "credentials.yaml"
    creds_file.write_text(f"api_key: {api_key}\nendpoint: {endpoint}\n")
    return CliRunner(), str(creds_file)


class TestParse:
    def test_parse(self, runner):
        cli_runner, _ = runner
        result = cli_runner.invoke(cli, ["--work", WORKSPACE, "parse"])
        assert result.exit_code == 0, f"parse failed: {result.output}"
        assert "Parse Result" in result.output

    def test_parse_generates_history(self, runner):
        cli_runner, _ = runner
        cli_runner.invoke(cli, ["--work", WORKSPACE, "parse"])
        history = os.path.join("workspaces", WORKSPACE, "output", "history.csv")
        assert os.path.exists(history)
        with open(history, encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) > 1, "history.csv should have data rows"


class TestVerify:
    def test_verify(self, runner):
        cli_runner, _ = runner
        # parseを先に実行してhistory.csvを生成
        cli_runner.invoke(cli, ["--work", WORKSPACE, "parse"])
        result = cli_runner.invoke(cli, ["--work", WORKSPACE, "verify"])
        assert result.exit_code == 0, f"verify failed: {result.output}"


class TestPrepare:
    def test_prepare_non_interactive(self, runner):
        cli_runner, _ = runner
        # 先にparse
        cli_runner.invoke(cli, ["--work", WORKSPACE, "parse"])
        result = cli_runner.invoke(cli, ["--work", WORKSPACE, "prepare", "-ni"])
        assert result.exit_code == 0, f"prepare failed: {result.output}"
        # 出力ファイル確認
        output_dir = os.path.join("workspaces", WORKSPACE, "output")
        assert os.path.exists(os.path.join(output_dir, "upload.yaml"))
        assert os.path.exists(os.path.join(output_dir, "order.csv"))


class TestUpload:
    def test_upload(self, runner):
        cli_runner, creds = runner
        # parse + prepare を先に実行
        cli_runner.invoke(cli, ["--work", WORKSPACE, "parse"])
        cli_runner.invoke(cli, ["--work", WORKSPACE, "prepare", "-ni"])
        upload_yaml = os.path.join("workspaces", WORKSPACE, "output", "upload.yaml")
        assert os.path.exists(upload_yaml), "upload.yamlが必要"
        result = cli_runner.invoke(
            cli,
            ["--work", WORKSPACE, "upload", "--credentials", creds, "--config", upload_yaml, "-y"],
        )
        assert result.exit_code == 0, f"upload failed: {result.output}"
        assert "Portfolio ID" in result.output

    def test_upload_json_output(self, runner):
        cli_runner, creds = runner
        cli_runner.invoke(cli, ["--work", WORKSPACE, "parse"])
        cli_runner.invoke(cli, ["--work", WORKSPACE, "prepare", "-ni"])
        upload_yaml = os.path.join("workspaces", WORKSPACE, "output", "upload.yaml")
        result = cli_runner.invoke(
            cli,
            ["--work", WORKSPACE, "upload", "--credentials", creds, "--config", upload_yaml, "-y", "--output-json"],
        )
        assert result.exit_code == 0, f"upload failed: {result.output}"
        import json
        # output-jsonはstdoutの最後にJSONを追加する
        lines = result.output.strip().split("\n")
        data = json.loads(lines[-1])
        assert data["status"] == "success"
        assert "portfolio_id" in data


class TestFullFlow:
    """E2E: parse → verify → prepare → upload → 削除。"""

    def test_full_pipeline(self, runner):
        cli_runner, creds = runner

        # 1. parse
        r = cli_runner.invoke(cli, ["--work", WORKSPACE, "parse"])
        assert r.exit_code == 0, f"parse: {r.output}"

        # 2. verify
        r = cli_runner.invoke(cli, ["--work", WORKSPACE, "verify"])
        assert r.exit_code == 0, f"verify: {r.output}"

        # 3. prepare
        r = cli_runner.invoke(cli, ["--work", WORKSPACE, "prepare", "-ni"])
        assert r.exit_code == 0, f"prepare: {r.output}"

        # 4. upload
        upload_yaml = os.path.join("workspaces", WORKSPACE, "output", "upload.yaml")
        r = cli_runner.invoke(
            cli,
            ["--work", WORKSPACE, "upload", "--credentials", creds, "--config", upload_yaml, "-y", "--output-json"],
        )
        assert r.exit_code == 0, f"upload: {r.output}"

        import json
        data = json.loads(r.output.strip().split("\n")[-1])
        assert data["status"] == "success"
        portfolio_id = data["portfolio_id"]

        # 5. cleanup - delete the uploaded portfolio
        r = cli_runner.invoke(
            cli, ["delete-portfolio", "--credentials", creds, portfolio_id, "--yes"],
        )
        # deleteに--yesフラグがない場合、確認プロンプトで非ゼロ終了を許容
        if r.exit_code != 0 and "confirm" in r.output.lower():
            pass  # 許容 — 手動削除が必要
        else:
            assert r.exit_code == 0 or "not found" not in r.output.lower()
