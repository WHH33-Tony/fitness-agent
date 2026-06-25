from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.runtime_config import (
    dashscope_api_key_configured,
    get_dashscope_api_key,
    get_xfyun_credentials,
    set_dashscope_api_key,
    set_xfyun_credentials,
    xfyun_configured,
)
from app.services.xfyun_tts import list_voices

router = APIRouter(prefix="/config", tags=["配置"])


class ApiKeyIn(BaseModel):
    dashscope_api_key: str = Field(default="", max_length=200)


class XfyunConfigIn(BaseModel):
    app_id: str = Field(default="", max_length=64)
    api_key: str = Field(default="", max_length=128)
    api_secret: str = Field(default="", max_length=128)


class XfyunPreviewIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    voice_type: str = Field(default="xiaoyan", max_length=64)


@router.get("/apikey/status")
def apikey_status() -> dict:
    return {"ok": True, "dashscope_api_key_set": dashscope_api_key_configured()}


@router.post("/apikey")
def set_apikey(payload: ApiKeyIn) -> dict:
    """
    写入并持久化 API Key，供所有用户共用（桌面版管理员配置一次即可）。
    """
    set_dashscope_api_key((payload.dashscope_api_key or "").strip())
    return {"ok": True, "dashscope_api_key_set": bool(get_dashscope_api_key())}


@router.get("/xfyun/status")
def xfyun_status() -> dict:
    creds = get_xfyun_credentials()
    return {
        "ok": True,
        "xfyun_configured": xfyun_configured(),
        "app_id": creds["app_id"],
        "api_key_set": bool(creds["api_key"]),
        "api_secret_set": bool(creds["api_secret"]),
    }


@router.post("/xfyun")
def set_xfyun_config(payload: XfyunConfigIn) -> dict:
    set_xfyun_credentials(payload.app_id, payload.api_key, payload.api_secret)
    return {"ok": True, "xfyun_configured": xfyun_configured()}


def _synthesize_or_raise(text: str, voice_type: str) -> dict[str, str]:
    from app.services.xfyun_tts import synthesize_speech_result

    if not xfyun_configured():
        raise HTTPException(status_code=400, detail="请先填写完整的 APPID、APIKey、APISecret")
    result, error = synthesize_speech_result(text, voice_type, get_settings().upload_dir)
    if not result:
        raise HTTPException(
            status_code=400,
            detail=error or "讯飞合成失败，请检查 APPID、APIKey、APISecret 是否正确",
        )
    return result


@router.post("/xfyun/test")
def test_xfyun_config() -> dict:
    result = _synthesize_or_raise("语音合成测试成功", "xiaoyan")
    return {"ok": True, **result}


@router.post("/xfyun/preview")
def preview_xfyun(payload: XfyunPreviewIn) -> dict:
    result = _synthesize_or_raise(payload.text, payload.voice_type)
    return {"ok": True, **result}


@router.get("/xfyun/voices")
def xfyun_voices() -> list[dict[str, str]]:
    return list_voices()
