"""讯飞在线语音合成（WebSocket v2）。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import uuid
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time

import websocket

from app.core.runtime_config import get_xfyun_credentials
from app.services.qa_service import sanitize_answer_text

logger = logging.getLogger(__name__)

TTS_HOST = "tts-api.xfyun.cn"
TTS_PATH = "/v2/tts"
TTS_MAX_CHARS = 1800

VOICE_CATALOG: list[dict[str, str]] = [
    {"id": "xiaoyan", "name": "讯飞小燕", "gender": "female", "desc": "温暖亲切女声", "tier": "basic"},
    {"id": "aisxping", "name": "讯飞小萍", "gender": "female", "desc": "明亮活泼女声", "tier": "basic"},
    {"id": "aisjinger", "name": "讯飞小婧", "gender": "female", "desc": "年轻甜美女声", "tier": "basic"},
    {"id": "aisjiuxu", "name": "讯飞许久", "gender": "male", "desc": "磁性沉稳男声", "tier": "basic"},
    {"id": "xiaoyu", "name": "讯飞小宇", "gender": "male", "desc": "亲切自然男声", "tier": "basic"},
    {"id": "xiaofeng", "name": "讯飞小峰", "gender": "male", "desc": "成熟稳重男声", "tier": "basic"},
    {"id": "x4_yezi", "name": "讯飞小露", "gender": "female", "desc": "亲切女声", "tier": "special"},
    {"id": "x6_lingxiaoxuan_assist", "name": "聆小璇", "gender": "female", "desc": "助理女声", "tier": "special"},
    {"id": "x6_lingxiaoyao_emo", "name": "聆小瑶", "gender": "female", "desc": "情感女声", "tier": "special"},
    {"id": "x4_lingfeizhe_emo", "name": "聆飞哲", "gender": "male", "desc": "情感男声", "tier": "special"},
    {"id": "x4_qige", "name": "讯飞七哥", "gender": "male", "desc": "磁性男声", "tier": "special"},
]

_LEGACY_VOICE_MAP = {
    "longxiaochun": "xiaoyan",
    "longxiaoxia": "aisxping",
    "longxiaocheng": "aisjiuxu",
    # 旧版错误 vcn，控制台已开通但 API 需用新版参数名
    "x2_qige": "x4_qige",
    "x4_lingxiaoxuan_assist": "x6_lingxiaoxuan_assist",
    "x4_lingxiaoyao_emo": "x6_lingxiaoyao_emo",
}

_VALID_VOICE_IDS = {item["id"] for item in VOICE_CATALOG}


def list_voices() -> list[dict[str, str]]:
    return [dict(item) for item in VOICE_CATALOG]


def resolve_voice_type(voice_type: str | None) -> str:
    vt = str(voice_type or "").strip()
    if not vt:
        return "xiaoyan"
    if vt in _LEGACY_VOICE_MAP:
        return _LEGACY_VOICE_MAP[vt]
    if vt in _VALID_VOICE_IDS:
        return vt
    # 讯飞控制台「特色发音人」的 vcn 参数（如 x4_yezi、x6_feizheChat_pro）
    if re.match(r"^x[2-6]_", vt) or vt.startswith("x_"):
        return vt
    return "xiaoyan"


def prepare_tts_text(text: str) -> str:
    cleaned = sanitize_answer_text(str(text or ""))
    cleaned = re.sub(r"__MEAL_PLAN__[\s\S]*?__END_MEAL_PLAN__", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > TTS_MAX_CHARS:
        cleaned = cleaned[:TTS_MAX_CHARS].rstrip() + "。"
    return cleaned


def _build_ws_url(api_key: str, api_secret: str) -> str:
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    signature_origin = f"host: {TTS_HOST}\ndate: {date}\nGET {TTS_PATH} HTTP/1.1"
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
    query = urlencode({"authorization": authorization, "date": date, "host": TTS_HOST})
    return f"wss://{TTS_HOST}{TTS_PATH}?{query}"


def _synthesize_mp3_bytes(text: str, vcn: str, app_id: str, api_key: str, api_secret: str) -> bytes:
    url = _build_ws_url(api_key, api_secret)
    audio_chunks: list[bytes] = []
    error_holder: list[str] = []

    payload = {
        "common": {"app_id": app_id},
        "business": {
            "aue": "lame",
            "sfl": 1,
            "auf": "audio/L16;rate=16000",
            "vcn": vcn,
            "speed": 50,
            "volume": 50,
            "pitch": 50,
            "tte": "UTF8",
        },
        "data": {
            "status": 2,
            "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
        },
    }

    def on_message(_ws: websocket.WebSocketApp, message: str) -> None:
        try:
            msg = json.loads(message)
        except json.JSONDecodeError:
            error_holder.append("讯飞 TTS 返回非 JSON 数据")
            _ws.close()
            return
        code = int(msg.get("code", -1))
        if code != 0:
            detail = str(msg.get("message") or msg.get("desc") or f"讯飞 TTS 失败(code={code})")
            error_holder.append(f"code={code} {detail}")
            _ws.close()
            return
        data = msg.get("data") or {}
        audio_b64 = data.get("audio")
        if audio_b64:
            audio_chunks.append(base64.b64decode(audio_b64))
        if int(data.get("status", 0)) == 2:
            _ws.close()

    def on_open(ws: websocket.WebSocketApp) -> None:
        ws.send(json.dumps(payload))

    def on_error(_ws: websocket.WebSocketApp, error: Exception) -> None:
        error_holder.append(str(error))

    ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message, on_error=on_error)
    ws.run_forever()
    if error_holder:
        raise RuntimeError(error_holder[0])
    if not audio_chunks:
        raise RuntimeError("讯飞 TTS 未返回音频数据")
    return b"".join(audio_chunks)


def synthesize_speech_result(
    text: str, voice_type: str | None, upload_dir: str
) -> tuple[dict[str, str] | None, str | None]:
    creds = get_xfyun_credentials()
    if not creds["configured"]:
        return None, "讯飞语音合成未配置，请在管理控制台填写 APPID、APIKey、APISecret"

    cleaned = prepare_tts_text(text)
    if not cleaned:
        return None, "播报文本为空或无效"

    vcn = resolve_voice_type(voice_type)
    try:
        audio_bytes = _synthesize_mp3_bytes(
            cleaned,
            vcn,
            creds["app_id"],
            creds["api_key"],
            creds["api_secret"],
        )
    except Exception as exc:
        logger.exception("讯飞 TTS 合成失败 voice=%s", vcn)
        message = str(exc).strip() or "讯飞合成失败"
        lower = message.lower()
        # 11200 的原文也常带 "licc failed"，必须先于 10005 判断，否则会误报为密钥错误
        if "code=11200" in lower or "no license" in lower or "未授权" in message:
            message = (
                f"发音人「{vcn}」未开通授权（讯飞错误 11200）。"
                f"若控制台显示已开通，可能是 vcn 参数与控制台不一致，请重新选择音色后保存；"
                f"或先改用基础发音人（如讯飞小燕）。"
            )
        elif "code=10005" in lower or "licc" in lower:
            message = (
                "讯飞 APPID 授权失败(licc fail)。请检查 APPID、APIKey、APISecret 是否正确且不要填反，"
                "并确认已在讯飞控制台开通「在线语音合成」服务"
            )
        elif "401" in message or "apikey not found" in lower:
            message = "讯飞 APIKey 无效，请在管理控制台重新填写并保存讯飞配置（注意 APIKey 与 APISecret 不要填反）"
        elif "vcn" in lower or "发音人" in message:
            message = f"发音人 {vcn} 不可用，请前往讯飞开放平台控制台开通该音色"
        return None, message

    out_dir = os.path.join(upload_dir, "tts")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.mp3"
    out_path = os.path.join(out_dir, filename)
    with open(out_path, "wb") as fp:
        fp.write(audio_bytes)
    return (
        {
            "audio_url": f"/uploads/tts/{filename}",
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "vcn": vcn,
        },
        None,
    )


def synthesize_and_save(text: str, voice_type: str | None, upload_dir: str) -> str | None:
    result, _ = synthesize_speech_result(text, voice_type, upload_dir)
    return result["audio_url"] if result else None
