# Printer Monitor

Сервис для мониторинга 3D-принтеров с Moonraker API, уведомлениями в Telegram и учётом событий печати.

Приложение периодически опрашивает принтеры, отслеживает изменения их состояний и сохраняет историю печати в SQLite. Интеграция со Spoolman позволяет получать сведения о филаменте.

## Возможности

- Мониторинг нескольких 3D-принтеров через Moonraker API.
- Уведомления в Telegram о начале, завершении и прерывании печати.
- Уведомления о потере и восстановлении соединения.
- Интеграция со Spoolman для отображения информации о филаменте.
- Сохранение истории событий печати в SQLite.
- Сохранение состояния мониторинга между перезапусками.
- Кеширование запросов к Spoolman и повторные попытки подключения при ошибках.
- Автоматический запуск через systemd на Linux.

## Пример уведомления

При завершении печати бот отправляет сообщение следующего вида:

```text
✅ FBR3_01: Печать завершена
📄 Файл: model.gcode
⏱️ Время: 1 ч 20 мин

──────────────
🧵 Филамент: Example PLA (PLA)
🧪 Расход: 12.50 г
⚖️ Остаток: 800.0 г
```

Значения в примере условные. Фактическое содержимое уведомления зависит от состояния принтера и доступности данных Spoolman.


## Стек

Python · Requests · Moonraker API · Spoolman API · Telegram Bot API · SQLite · PyYAML · pytest

## Требования

- Python 3.10+ (рекомендуется 3.11+).
- Для уведомлений необходимы Telegram-бот и ID чата. Учётные данные задаются через `.env` или `config.yaml`.

## Локальный запуск

Локальный запуск подходит для разработки и проверки приложения. Рекомендуется использовать виртуальное окружение Python, чтобы изолировать зависимости проекта.


### Linux/macOS

1. (Опционально) Создайте виртуальное окружение:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Подготовьте конфиг:
   ```bash
   cp config.example.yaml config.yaml
   nano config.yaml
   ```
   
   Отредактируйте `config.yaml`: укажите адреса принтеров и, при использовании Spoolman, адрес его API. Все доступные параметры приведены в `config.example.yaml`.

4. Создайте `.env` с секретами:
   ```bash
   cat <<'EOF' > .env
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   EOF
   ```
5. Запуск:
   ```bash
   python -m src
   ```

### Windows PowerShell

1. Создайте виртуальное окружение:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Установите зависимости:
   ```powershell
   pip install -r requirements.txt
   ```
3. Подготовьте конфиг:
   ```powershell
   Copy-Item config.example.yaml config.yaml
   notepad config.yaml
   ```

   Отредактируйте `config.yaml`: укажите адреса принтеров и, при использовании Spoolman, адрес его API. Все доступные параметры приведены в `config.example.yaml`.

4. Создайте `.env` с секретами:
   ```powershell
   @"
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   "@ | Set-Content -Path .env
   ```
5. Запуск:
   ```powershell
   py -m src
   ```

## Установка на устройство

Этот сценарий описывает подготовку окружения на устройстве (например, Raspberry Pi или мини-сервер), где приложение будет работать постоянно.

1. Подготовьте директорию проекта (пример):
   ```bash
   sudo mkdir -p /opt/printer_monitor
   sudo chown "$USER":"$USER" /opt/printer_monitor
   ```
2. Скопируйте проект в `/opt/printer_monitor`.
3. Создайте виртуальное окружение и установите зависимости:
   ```bash
   cd /opt/printer_monitor
   python3 -m venv .venv
   /opt/printer_monitor/.venv/bin/pip install -r requirements.txt
   ```
4. Создайте локальную конфигурацию и файл окружения:

   ```bash
   cp config.example.yaml config.yaml
   nano config.yaml
   nano .env
   chmod 600 .env
   ```

   В `.env` укажите:

   ```dotenv
   TELEGRAM_BOT_TOKEN=ваш_токен
   TELEGRAM_CHAT_ID=ваш_chat_id
   ```

   В `config.yaml` укажите адреса принтеров и Spoolman.

> Далее используйте systemd для автозапуска. **Ручная активация venv (`source .../activate`) для systemd не используется и не требуется.**

## Переменные окружения

- `TELEGRAM_BOT_TOKEN` — токен Telegram бота (обязателен).
- `TELEGRAM_CHAT_ID` — ID чата (обязателен).
- `MONITOR_CHECK_INTERVAL` — интервал опроса (сек).

## Интеграция со Spoolman

Spoolman используется для получения информации о филаменте и его остатке. Интеграция необязательна: без неё мониторинг принтеров и Telegram-уведомления продолжают работать.

Чтобы отключить Spoolman, оставьте адрес пустым в `config.yaml`:

```yaml
spoolman:
  url: ""
```

При недоступности Spoolman информация о филаменте отображается как неизвестная. Ошибки обращения к сервису не останавливают мониторинг принтеров.

## Автозапуск через systemd

Важно:
- **Не нужно и нельзя** активировать venv через `source .../activate` для systemd.
- Используйте **только абсолютные пути** (systemd не принимает `~`).
- Ручной запуск и systemd — разные сценарии. Выход из терминала или деактивация `.venv` **не влияет** на сервис.

Создайте файл сервиса:
```bash
sudo mkdir -p /etc/systemd/system
sudo nano /etc/systemd/system/printer-monitor.service
```

Содержимое `/etc/systemd/system/printer-monitor.service`:

> Замените `YOUR_LINUX_USERNAME` на имя непривилегированного пользователя Linux, от имени которого устанавливался проект. Узнать имя можно командой `whoami`. У этого пользователя должны быть права на чтение конфигурации и запись в каталоги `data/` и `logs/`. Указывать `$USER` непосредственно в service-файле не нужно.
```
[Unit]
Description=Printer Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=YOUR_LINUX_USERNAME
WorkingDirectory=/opt/printer_monitor
EnvironmentFile=/opt/printer_monitor/.env
ExecStart=/opt/printer_monitor/.venv/bin/python -m src
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

После создания:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now printer-monitor
sudo systemctl status printer-monitor
```

После перезагрузки сервис стартует автоматически, если он включён (`enabled`).

## Диагностика systemd

Диагностика:
```bash
systemctl status printer-monitor --no-pager -l
journalctl -xeu printer-monitor --no-pager
```

Частые ошибки:
- Неверный путь в `WorkingDirectory` или `ExecStart`.
- Отсутствует `.env` или неверный `EnvironmentFile`.
- Отсутствует `.venv` или зависимости не установлены.
- Неверный модуль запуска (`-m src`) или он переименован.

## Логи и данные

- Логи: `logs/printer_monitor.log`
- Состояния: `data/printer_states.json`
- База событий: `data/print_events.db`

## Тесты

Установите dev-зависимости и запустите `pytest`:
```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Лицензия

Проект распространяется по лицензии MIT. Подробнее — в файле [LICENSE](LICENSE).
