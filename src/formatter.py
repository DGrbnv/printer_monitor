from html import escape


def format_remaining_weight(spool):
    if not spool:
        return "неизвестно"

    weight = spool.get("remaining_weight")

    if weight is None:
        return "неизвестно"

    try:
        return f"{float(weight):.1f} г"
    except (TypeError, ValueError):
        return "неизвестно"

def format_time(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} сек"
    if seconds < 3600:
        return f"{seconds // 60} мин"
    return f"{seconds // 3600} ч {(seconds % 3600) // 60} мин"

def start_message(printer, filename, spool, filament_name, eta=None, progress=None):
    printer = escape(str(printer))
    filename = escape(str(filename))
    filament_name = escape(str(filament_name))

    msg = (
        f"🖨️ <b>{printer}</b>: Начал печать 🚀\n"
        f"📄 <b>Файл:</b> {filename}\n"
    )

    if eta:
        msg += f"⏰ <b>Завершение:</b> {eta.strftime('%d.%m %H:%M')}\n"
    if progress is not None and progress > 0:
        msg += f"📊 <b>Прогресс:</b> {progress:.0f}%\n"

    if spool:
        msg += (
            "\n<b>──────────────</b>\n"
            f"🧵 <b>Филамент:</b> {filament_name}\n"
            f"⚖️ <b>Остаток:</b> {format_remaining_weight(spool)}"
        )
    else:
        msg += (
            "\n<b>──────────────</b>\n"
            "🧵 <b>Филамент:</b> неизвестно\n"
            "💡 <i>Добавьте катушку в Spoolman</i>"
        )

    return msg

def end_message(
    printer,
    filename,
    duration,
    grams,
    spool,
    filament_name,
    state,
    reason=None
):
    printer = escape(str(printer))
    filename = escape(str(filename))
    filament_name = escape(str(filament_name))

    emoji = {
        "complete": "✅",
        "cancelled": "🚫",
        "error": "❌",
        "offline": "⚠️"
    }[state]
    text = {
        "complete": "Печать завершена",
        "cancelled": "Печать отменена",
        "error": "Ошибка печати",
        "offline": "Потеряна связь с принтером"
    }[state]
    remaining = format_remaining_weight(spool)

    msg = (
        f"{emoji} <b>{printer}</b>: {text}\n"
        f"📄 <b>Файл:</b> {filename}\n"
        f"⏱️ <b>Время:</b> {format_time(duration)}\n"
        "\n<b>──────────────</b>\n"
        f"🧵 <b>Филамент:</b> {filament_name}\n"
        f"⚖️ <b>Остаток:</b> {remaining}"
    )
    if grams is not None:
        msg = msg.replace(
            f"⚖️ <b>Остаток:</b> {remaining}",
            f"🧪 <b>Расход:</b> {grams:.2f} г\n"
            f"⚖️ <b>Остаток:</b> {remaining}"
        )
    if reason:
        msg += f"\n🧭 <b>Причина:</b> {escape(str(reason))}"
    return msg


def offline_message(printer, last_state, last_filename=None):
    printer = escape(str(printer))
    details = ""
    if last_state:
        details += f"\n📟 <b>Последнее состояние:</b> {escape(str(last_state))}"
    if last_filename:
        details += f"\n📄 <b>Файл:</b> {escape(str(last_filename))}"
    return f"⚠️ <b>{printer}</b>: Принтер недоступен{details}"


def recovery_message(printer, offline_since, recovered_at):
    printer = escape(str(printer))
    down_seconds = int((recovered_at - offline_since).total_seconds())
    return (
        f"✅ <b>{printer}</b>: Соединение восстановлено\n"
        f"⏱️ <b>Оффлайн:</b> {format_time(max(0, down_seconds))}"
    )
