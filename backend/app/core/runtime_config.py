from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.config import get_settings


def _config_path() -> Path:
    custom = str(os.environ.get("RUNTIME_CONFIG_PATH") or "").strip()
    if custom:
        return Path(custom)
    return Path("data/runtime_config.json")


def _read_file() -> dict:
    path = _config_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_file(data: dict) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _pick_setting(settings_value: str, file_value: str, env_value: str) -> str:
    for candidate in (settings_value, file_value, env_value):
        cleaned = str(candidate or "").strip()
        if cleaned:
            return cleaned
    return ""


def bootstrap_runtime_settings() -> None:
    """启动时从环境变量与本地文件恢复运行时配置（桌面端管理员保存一次即可）。"""
    settings = get_settings()
    data = _read_file()
    settings.dashscope_api_key = _pick_setting(
        settings.dashscope_api_key,
        str(data.get("dashscope_api_key") or ""),
        os.environ.get("DASHSCOPE_API_KEY", ""),
    )
    settings.xfyun_app_id = _pick_setting(
        settings.xfyun_app_id,
        str(data.get("xfyun_app_id") or ""),
        os.environ.get("XFYUN_APP_ID", ""),
    )
    settings.xfyun_api_key = _pick_setting(
        settings.xfyun_api_key,
        str(data.get("xfyun_api_key") or ""),
        os.environ.get("XFYUN_API_KEY", ""),
    )
    settings.xfyun_api_secret = _pick_setting(
        settings.xfyun_api_secret,
        str(data.get("xfyun_api_secret") or ""),
        os.environ.get("XFYUN_API_SECRET", ""),
    )


def get_dashscope_api_key() -> str:
    settings = get_settings()
    key = str(settings.dashscope_api_key or "").strip()
    if key:
        return key
    return str(_read_file().get("dashscope_api_key") or "").strip()


def set_dashscope_api_key(key: str) -> None:
    cleaned = (key or "").strip()
    settings = get_settings()
    settings.dashscope_api_key = cleaned
    data = _read_file()
    data["dashscope_api_key"] = cleaned
    _write_file(data)


def dashscope_api_key_configured() -> bool:
    return bool(get_dashscope_api_key())


def get_xfyun_credentials() -> dict[str, str | bool]:
    settings = get_settings()
    data = _read_file()
    app_id = str(settings.xfyun_app_id or data.get("xfyun_app_id") or "").strip()
    api_key = str(settings.xfyun_api_key or data.get("xfyun_api_key") or "").strip()
    api_secret = str(settings.xfyun_api_secret or data.get("xfyun_api_secret") or "").strip()
    return {
        "app_id": app_id,
        "api_key": api_key,
        "api_secret": api_secret,
        "configured": bool(app_id and api_key and api_secret),
    }


def set_xfyun_credentials(app_id: str, api_key: str, api_secret: str) -> None:
    settings = get_settings()
    existing = get_xfyun_credentials()
    cleaned_app_id = (app_id or "").strip() or str(existing["app_id"] or "")
    cleaned_api_key = (api_key or "").strip() or str(existing["api_key"] or "")
    cleaned_api_secret = (api_secret or "").strip() or str(existing["api_secret"] or "")
    settings.xfyun_app_id = cleaned_app_id
    settings.xfyun_api_key = cleaned_api_key
    settings.xfyun_api_secret = cleaned_api_secret
    data = _read_file()
    data["xfyun_app_id"] = cleaned_app_id
    data["xfyun_api_key"] = cleaned_api_key
    data["xfyun_api_secret"] = cleaned_api_secret
    _write_file(data)


def xfyun_configured() -> bool:
    return bool(get_xfyun_credentials()["configured"])
