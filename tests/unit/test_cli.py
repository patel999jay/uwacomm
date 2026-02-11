"""Tests for CLI tool."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_help() -> None:
    """Test CLI --help flag."""
    result = subprocess.run(
        [sys.executable, "-m", "uwacomm.cli.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "uwacomm: Underwater Communications Codec" in result.stdout
    assert "--analyze" in result.stdout


def test_cli_version() -> None:
    """Test CLI --version flag."""
    result = subprocess.run(
        [sys.executable, "-m", "uwacomm.cli.main", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "uwacomm 0.1.0" in result.stdout


def test_cli_analyze_example_file() -> None:
    """Test CLI --analyze with a real example file."""
    example_file = Path("examples/framing_example.py")
    if not example_file.exists():
        pytest.skip("Example file not found")

    result = subprocess.run(
        [sys.executable, "-m", "uwacomm.cli.main", "--analyze", str(example_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "uwacomm: Underwater Communications Codec" in result.stdout
    assert "messages loaded" in result.stdout
    assert "StatusReport" in result.stdout or "CommandMessage" in result.stdout


def test_cli_analyze_missing_file() -> None:
    """Test CLI --analyze with missing file."""
    result = subprocess.run(
        [sys.executable, "-m", "uwacomm.cli.main", "--analyze", "nonexistent.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Error" in result.stderr or "not found" in result.stderr.lower()


def test_cli_no_args() -> None:
    """Test CLI with no arguments (should show help)."""
    result = subprocess.run(
        [sys.executable, "-m", "uwacomm.cli.main"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "uwacomm: Underwater Communications Codec" in result.stdout
