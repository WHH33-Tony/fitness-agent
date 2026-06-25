"""讯飞语音听写（IAT WebSocket v2）。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import logging
import wave
from datetime import datetime
from time import mktime, sleep
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time

import websocket

from app.core.runtime_config import get_xfyun_credentials

logger = logging.getLogger(__name__)

IAT_HOST = "iat-api.xfyun.cn"
IAT_PATH = "/v2/iat"
FRAME_SIZE = 1280


def _build_ws_url(api_key: str, api_secret: str) -> str:
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    signature_origin = f"host: {IAT_HOST}\ndate: {date}\nGET {IAT_PATH} HTTP/1.1"
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
    query = urlencode({"authorization": authorization, "date": date, "host": IAT_HOST})
    return f"wss://{IAT_HOST}{IAT_PATH}?{query}"


def _extract_pcm_from_wav(data: bytes) -> bytes:
    with wave.open(io.BytesIO(data), "rb") as wf:
        if wf.getsampwidth() != 2:
            raise ValueError("仅支持 16bit WAV")
        if wf.getframerate() != 16000:
            raise ValueError("仅支持 16kHz 采样率")
        if wf.getnchannels() != 1:
            raise ValueError("仅支持单声道 WAV")
        return wf.readframes(wf.getnframes())


def prepare_pcm_audio(data: bytes, *, filename: str = "") -> bytes:
    lower = (filename or "").lower()
    if lower.endswith(".wav") or data[:4] == b"RIFF":
        return _extract_pcm_from_wav(data)
    return data


def _parse_iat_words(payload: dict) -> str:
    data = payload.get("data") or {}
    result = data.get("result") or {}
    words: list[str] = []
    for item in result.get("ws") or []:
        for cw in item.get("cw") or []:
            word = str(cw.get("w") or "").strip()
            if word:
                words.append(word)
    return "".join(words).strip()


def transcribe_pcm_bytes(pcm_bytes: bytes) -> tuple[str | None, str | None]:
    creds = get_xfyun_credentials()
    if not creds["configured"]:
        return None, "讯飞语音识别未配置，请在管理控制台填写 APPID、APIKey、APISecret"

    if not pcm_bytes:
        return None, "音频数据为空"

    url = _build_ws_url(creds["api_key"], creds["api_secret"])
    transcripts: list[str] = []
    error_holder: list[str] = []
    chunks = [pcm_bytes[i : i + FRAME_SIZE] for i in range(0, len(pcm_bytes), FRAME_SIZE)] or [b""]

    def on_message(_ws: websocket.WebSocketApp, message: str) -> None:
        try:
            msg = json.loads(message)
        except json.JSONDecodeError:
            error_holder.append("讯飞 IAT 返回非 JSON 数据")
            _ws.close()
            return
        code = int(msg.get("code", -1))
        if code != 0:
            detail = str(msg.get("message") or msg.get("desc") or f"讯飞 IAT 失败(code={code})")
            error_holder.append(f"code={code} {detail}")
            _ws.close()
            return
        text = _parse_iat_words(msg)
        if text:
            transcripts.append(text)
        if int((msg.get("data") or {}).get("status", 0)) == 2:
            _ws.close()

    def _send_frame(ws: websocket.WebSocketApp, *, status: int, chunk: bytes, with_meta: bool) -> None:
        frame: dict = {
            "data": {
                "status": status,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
                "audio": base64.b64encode(chunk).decode("utf-8"),
            }
        }
        if with_meta:
            frame["common"] = {"app_id": creds["app_id"]}
            frame["business"] = {
                "language": "zh_cn",
                "domain": "iat",
                "accent": "mandarin",
                "vad_eos": 3000,
            }
        ws.send(json.dumps(frame))

    def on_open(ws: websocket.WebSocketApp) -> None:
        _send_frame(ws, status=0, chunk=chunks[0], with_meta=True)
        sleep(0.04)
        for chunk in chunks[1:]:
            _send_frame(ws, status=1, chunk=chunk, with_meta=False)
            sleep(0.04)
        _send_frame(ws, status=2, chunk=b"", with_meta=False)

    def on_error(_ws: websocket.WebSocketApp, error: Exception) -> None:
        error_holder.append(str(error))

    ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message, on_error=on_error)
    ws.run_forever()
    if error_holder:
        logger.warning("讯飞 IAT 失败: %s", error_holder[0])
        return None, error_holder[0]
    text = "".join(transcripts).strip()
    if not text:
        return None, "未识别到有效语音内容，请靠近麦克风清晰说话后重试"
    return text, None
