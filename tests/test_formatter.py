
from datetime import datetime

from src.formatter import (
    end_message,
    format_remaining_weight,
    offline_message,
    recovery_message,
    start_message,
)


def test_start_message_without_spool_or_eta():
    message = start_message(
        printer="P1",
        filename="test.gcode",
        spool=None,
        filament_name="Неизвестно",
        eta=None,
        progress=None,
    )

    assert "Завершение" not in message
    assert "Прогресс" not in message
    assert "Филамент:</b> неизвестно" in message
    assert "Добавьте катушку" in message


def test_start_message_without_progress_for_zero():
    message = start_message(
        printer="P1",
        filename="test.gcode",
        spool=None,
        filament_name="Неизвестно",
        eta=None,
        progress=0.0,
    )

    assert "Прогресс" not in message


def test_end_message_without_spool():
    message = end_message(
        printer="P1",
        filename="test.gcode",
        duration=120,
        grams=1.23,
        spool=None,
        filament_name="Неизвестно",
        state="complete",
        reason=None,
    )

    assert "Остаток:</b> неизвестно" in message
    assert "Причина" not in message


def test_start_message_escapes_html():
    message = start_message(
        printer="P&1",
        filename="model <test>.gcode",
        spool={"remaining_weight": None},
        filament_name="PLA & PETG",
    )

    assert "<b>P&amp;1</b>" in message
    assert "model &lt;test&gt;.gcode" in message
    assert "PLA &amp; PETG" in message
    assert "Остаток:</b> неизвестно" in message


def test_end_message_escapes_html():
    message = end_message(
        printer="P<1>",
        filename="model & test.gcode",
        duration=60,
        grams=None,
        spool=None,
        filament_name="PLA <Silk>",
        state="error",
        reason="Ошибка <sensor> & timeout",
    )

    assert "<b>P&lt;1&gt;</b>" in message
    assert "model &amp; test.gcode" in message
    assert "PLA &lt;Silk&gt;" in message
    assert "Ошибка &lt;sensor&gt; &amp; timeout" in message


def test_connection_messages_escape_html():
    offline = offline_message(
        printer="P&1",
        last_state="printing",
        last_filename="model <test>.gcode",
    )

    assert "<b>P&amp;1</b>" in offline
    assert "model &lt;test&gt;.gcode" in offline

    recovered = recovery_message(
        printer="P&1",
        offline_since=datetime(2026, 1, 1, 12, 0),
        recovered_at=datetime(2026, 1, 1, 12, 2),
    )

    assert "<b>P&amp;1</b>" in recovered
    assert "2 мин" in recovered


def test_remaining_weight_handles_invalid_values():
    assert format_remaining_weight(None) == "неизвестно"
    assert format_remaining_weight({}) == "неизвестно"
    assert format_remaining_weight({"remaining_weight": None}) == "неизвестно"
    assert format_remaining_weight({"remaining_weight": "invalid"}) == "неизвестно"
    assert format_remaining_weight({"remaining_weight": 42.5}) == "42.5 г"
