from __future__ import annotations

import json
from pathlib import Path

from quality_gate_demo.cli import main


def test_cli_quotes_an_order_file(tmp_path: Path, capsys: object) -> None:
    request_path = tmp_path / "order.json"
    request_path.write_text(
        json.dumps(
            {
                "subtotal_cents": 6000,
                "membership": "premium",
                "coupon_percent": 10,
                "express": False,
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["quote", "--input", str(request_path)])

    assert exit_code == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert json.loads(captured.out) == {
        "subtotal_cents": 6000,
        "coupon_discount_cents": 600,
        "membership_discount_cents": 270,
        "shipping_cents": 0,
        "total_cents": 5130,
    }
    assert captured.err == ""


def test_cli_rejects_an_invalid_order_file(tmp_path: Path, capsys: object) -> None:
    request_path = tmp_path / "order.json"
    request_path.write_text('{"subtotal_cents": 0, "membership": "standard"}', encoding="utf-8")

    exit_code = main(["quote", "--input", str(request_path)])

    assert exit_code == 2
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert captured.out == ""
    assert "subtotal_cents" in captured.err


def test_cli_rejects_unknown_fields(tmp_path: Path, capsys: object) -> None:
    request_path = tmp_path / "order.json"
    request_path.write_text(
        '{"subtotal_cents": 1000, "membership": "standard", "admin": true}',
        encoding="utf-8",
    )

    exit_code = main(["quote", "--input", str(request_path)])

    assert exit_code == 2
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "unknown field" in captured.err
