from src.config import Config


def _write_config(tmp_path, spoolman_url="http://from-config:7912"):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "telegram:",
                "  bot_token: 'token'",
                "  chat_id: 'chat'",
                "printers:",
                "  P1:",
                "    url: 'http://printer:7125'",
                "spoolman:",
                f"  url: '{spoolman_url}'",
                "monitoring:",
                "  check_interval: 10",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def test_spoolman_url_comes_from_config_only(tmp_path, monkeypatch):
    config_path = _write_config(tmp_path, spoolman_url="http://from-config:7912")
    monkeypatch.setenv("SPOOLMAN_URL", "http://from-env:7912")

    cfg = Config(str(config_path))

    assert cfg.spoolman_url == "http://from-config:7912"


def test_spoolman_url_none_when_missing_in_config(tmp_path):
    config_path = _write_config(tmp_path, spoolman_url="")

    cfg = Config(str(config_path))

    assert cfg.spoolman_url == ""


def test_spoolman_is_optional_when_section_missing(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "telegram:",
                "  bot_token: 'token'",
                "  chat_id: 'chat'",
                "printers:",
                "  P1:",
                "    url: 'http://printer:7125'",
                "monitoring:",
                "  check_interval: 10",
            ]
        ),
        encoding="utf-8",
    )

    cfg = Config(str(config_path))

    assert cfg.spoolman_url is None
