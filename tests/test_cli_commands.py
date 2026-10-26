from __future__ import annotations
from click.testing import CliRunner

from huntly.cli import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "🎯 Huntly - AI-Powered Job Hunting Terminal Assistant" in result.output
    assert "scrape" in result.output
    assert "analyze" in result.output
    assert "enrich" in result.output
    assert "status" in result.output
    assert "top" in result.output
    assert "resume" in result.output
    assert "demo" in result.output


def test_cli_status():
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "Huntly System & Quota Status" in result.output
    assert "Total Jobs Indexed" in result.output


def test_cli_resume():
    runner = CliRunner()
    result = runner.invoke(cli, ["resume"])
    assert result.exit_code == 0
    assert "Reading resume from:" in result.output


def test_cli_top():
    runner = CliRunner()
    result = runner.invoke(cli, ["top", "--limit", "3"])
    assert result.exit_code == 0
    assert "Matching Opportunities" in result.output


def test_cli_scrape_options():
    runner = CliRunner()
    result = runner.invoke(cli, ["scrape", "--help"])
    assert result.exit_code == 0
    assert "--source" in result.output
    assert "all_free" in result.output
    assert "hn" in result.output
    assert "remoteok" in result.output
    assert "wwr" in result.output


def test_cli_analyze_options():
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "--limit" in result.output


def test_cli_demo():
    from unittest.mock import patch
    runner = CliRunner()
    with patch("huntly.app.HuntlyApp.run", return_value=None):
        result = runner.invoke(cli, ["demo"])
        assert result.exit_code == 0
