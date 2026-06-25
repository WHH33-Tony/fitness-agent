import json
import os
import hashlib
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.api.deps import RedisDep
from app.services.exercise_i18n import localize_exercise_fields

DEFAULT_PROVIDER = "oss_v1"
EXERCISEDB_PROVIDER = (os.getenv("EXERCISEDB_PROVIDER") or DEFAULT_PROVIDER).strip().lower()

# oss_v1: free tier (no API key), stable GIF URLs (static.exercisedb.dev)
OSS_V1_BASE = "https://oss.exercisedb.dev/api/v1"
# legacy: previous (may be disabled / paid / unstable). Keep for optional fallback if needed.
LEGACY_BASE = "https://exercisedb-api.vercel.app/api/v1"

# Allow overriding base URL explicitly (advanced usage / self-hosted).
EXERCISEDB_BASE = (os.getenv("EXERCISEDB_BASE_URL") or (OSS_V1_BASE if EXERCISEDB_PROVIDER == "oss_v1" else LEGACY_BASE)).strip()

EXERCISE_CACHE_VERSION = "v6"
router = APIRouter(prefix="/exercises", tags=["动作库"])

_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # .../backend
_IMAGE_CACHE_DIR = _BACKEND_ROOT / "static" / "exercise-cache"

COMMON_ERRORS: dict[str, list[str]] = {
    "chest": ["肩胛没有稳定，容易耸肩", "肘部过度外展", "核心松散导致身体晃动"],
    "back": ["借力摆动过大", "肩胛没有下沉收紧", "腰背代偿发力"],
    "waist": ["颈部过度用力", "核心没有持续收紧", "动作速度过快"],
    "upper legs": ["膝盖内扣", "脚跟离地", "躯干前倾过多"],
    "lower legs": ["落地缓冲不足", "踝关节控制不稳定", "动作节奏过快"],
    "shoulders": ["耸肩代偿", "手臂轨迹不稳定", "核心没有固定躯干"],
    "upper arms": ["肘部位置漂移", "身体借力摆动", "离心阶段控制不足"],
    "lower arms": ["手腕过度弯折", "前臂发力不稳定", "动作范围不足"],
    "cardio": ["落地冲击过大", "呼吸节奏紊乱", "核心松散导致姿态变形"],
}

STANDARD_POSE_TEMPLATES: dict[str, dict[str, Any]] = {
    "chest": {
        "main_angles": {"elbow": [70, 120], "shoulder": [45, 100], "torso": [150, 180]},
        "keypoints": ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"],
    },
    "back": {
        "main_angles": {"elbow": [45, 130], "shoulder": [20, 120], "torso": [145, 180]},
        "keypoints": ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_hip", "right_hip"],
    },
    "waist": {
        "main_angles": {"hip": [60, 130], "shoulder": [45, 120], "torso": [90, 170]},
        "keypoints": ["left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_knee", "right_knee"],
    },
    "upper legs": {
        "main_angles": {"knee": [70, 160], "hip": [65, 150], "torso": [145, 180]},
        "keypoints": ["left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"],
    },
    "default": {
        "main_angles": {"elbow": [60, 150], "shoulder": [30, 150], "torso": [140, 180]},
        "keypoints": ["shoulder", "elbow", "wrist", "hip", "knee", "ankle"],
    },
}

LOCAL_EXERCISES: list[dict[str, Any]] = [
    {
        "id": "local-push-up",
        "name": "push up",
        "bodyPart": "chest",
        "target": "pectorals",
        "secondaryMuscles": ["triceps", "deltoids", "abs"],
        "equipment": "body weight",
        "gifUrl": "https://v2.exercisedb.io/image/FysKiyLCRN6UA7",
        "instructions": ["双手略宽于肩支撑地面", "核心收紧，身体保持一条直线", "屈肘下降至胸部接近地面", "推起时不要塌腰，保持肩胛稳定"],
    },
    {
        "id": "local-wide-push-up",
        "name": "wide push up",
        "bodyPart": "chest",
        "target": "pectorals",
        "secondaryMuscles": ["triceps", "deltoids"],
        "equipment": "body weight",
        "gifUrl": "https://v2.exercisedb.io/image/ZSp2WVsFpSNkZ4",
        "instructions": ["双手比肩更宽", "下降时胸部主动靠近地面", "肘部不要过度外展", "推起时保持核心稳定"],
    },
    {
        "id": "local-squat",
        "name": "bodyweight squat",
        "bodyPart": "upper legs",
        "target": "quadriceps",
        "secondaryMuscles": ["glutes", "hamstrings", "abs"],
        "equipment": "body weight",
        "gifUrl": "https://v2.exercisedb.io/image/qJHsOiRxivMCo0",
        "instructions": ["双脚与肩同宽站立", "髋部向后坐，膝盖对准脚尖", "背部保持挺直", "下蹲后发力回到站立"],
    },
    {
        "id": "local-lunge",
        "name": "lunge",
        "bodyPart": "upper legs",
        "target": "quadriceps",
        "secondaryMuscles": ["glutes", "hamstrings"],
        "equipment": "body weight",
        "gifUrl": "https://v2.exercisedb.io/image/DLRaK7s7l1oRsm",
        "instructions": ["一脚向前迈步", "身体垂直下沉", "前膝对准脚尖", "后膝接近地面后回到起始位置"],
    },
    {
        "id": "local-plank",
        "name": "front plank",
        "bodyPart": "waist",
        "target": "abs",
        "secondaryMuscles": ["deltoids", "glutes"],
        "equipment": "body weight",
        "gifUrl": "https://v2.exercisedb.io/image/n1KJtQlRXGMkKn",
        "instructions": ["肘部位于肩部下方", "核心收紧", "头肩髋脚保持一条直线", "保持稳定呼吸"],
    },
    {
        "id": "local-crunch",
        "name": "crunch",
        "bodyPart": "waist",
        "target": "abs",
        "secondaryMuscles": [],
        "equipment": "body weight",
        "gifUrl": "https://v2.exercisedb.io/image/Lg75gaYurzkIxT",
        "instructions": ["仰卧屈膝", "腹部发力卷起上背", "颈部保持自然", "缓慢还原，不要借助手臂拉头"],
    },
    {
        "id": "local-pull-up",
        "name": "pull up",
        "bodyPart": "back",
        "target": "lats",
        "secondaryMuscles": ["biceps", "upper back"],
        "equipment": "body weight",
        "gifUrl": "https://v2.exercisedb.io/image/EV5CcrUBO7dhmK",
        "instructions": ["双手握杠，身体自然悬垂", "肩胛下沉，核心收紧", "背部发力将身体拉起", "缓慢下放回到悬垂"],
    },
    {
        "id": "local-dumbbell-row",
        "name": "dumbbell row",
        "bodyPart": "back",
        "target": "upper back",
        "secondaryMuscles": ["lats", "biceps"],
        "equipment": "dumbbell",
        "gifUrl": "https://v2.exercisedb.io/image/QoxJtQPhDoZxXU",
        "instructions": ["俯身保持背部平直", "单手握哑铃自然下垂", "肘部向后拉起哑铃", "肩胛收紧后缓慢下放"],
    },
    {
        "id": "local-shoulder-press",
        "name": "dumbbell shoulder press",
        "bodyPart": "shoulders",
        "target": "deltoids",
        "secondaryMuscles": ["triceps", "traps"],
        "equipment": "dumbbell",
        "gifUrl": "https://v2.exercisedb.io/image/UYqmGIKpO2rMzF",
        "instructions": ["双手持哑铃位于肩旁", "核心收紧，避免耸肩", "向上推举至手臂伸直", "缓慢下放回肩旁"],
    },
    {
        "id": "local-biceps-curl",
        "name": "dumbbell biceps curl",
        "bodyPart": "upper arms",
        "target": "biceps",
        "secondaryMuscles": ["forearms"],
        "equipment": "dumbbell",
        "gifUrl": "https://v2.exercisedb.io/image/O37UNSElY3pWvE",
        "instructions": ["双手持哑铃自然下垂", "保持肘部靠近身体", "弯举哑铃至胸前", "控制速度缓慢下放"],
    },
    {
        "id": "local-triceps-dip",
        "name": "bench dip",
        "bodyPart": "upper arms",
        "target": "triceps",
        "secondaryMuscles": ["deltoids", "pectorals"],
        "equipment": "body weight",
        "gifUrl": "https://v2.exercisedb.io/image/O3JOZHFTkmFP6I",
        "instructions": ["双手撑在凳沿", "身体靠近凳子下沉", "肘部向后弯曲", "肱三头肌发力推回起始位置"],
    },
    {
        "id": "local-jumping-jack",
        "name": "jumping jack",
        "bodyPart": "cardio",
        "target": "cardiovascular system",
        "secondaryMuscles": ["calves", "deltoids"],
        "equipment": "body weight",
        "gifUrl": "https://v2.exercisedb.io/image/ZiC0vb6c0BzAK7",
        "instructions": ["站立收紧核心", "跳起同时打开双腿并上举双手", "落地缓冲", "保持稳定节奏和呼吸"],
    },
    # lower legs
    {
        "id": "local-calf-raise",
        "name": "standing calf raise",
        "bodyPart": "lower legs",
        "target": "calves",
        "secondaryMuscles": ["soleus"],
        "equipment": "body weight",
        "gifUrl": "https://v2.exercisedb.io/image/9fXw1oQJYq3e8d",
        "instructions": ["站立，脚尖踩稳", "提踵至最高点", "顶端停顿1秒", "缓慢下放，保持核心稳定"],
    },
    {
        "id": "local-seated-calf-raise",
        "name": "seated calf raise",
        "bodyPart": "lower legs",
        "target": "calves",
        "secondaryMuscles": ["soleus"],
        "equipment": "leverage",
        "gifUrl": "https://v2.exercisedb.io/image/3g2bHqkTQn1d8A",
        "instructions": ["坐姿，小腿与脚踝固定", "脚跟下放到最低点", "提踵至最高点", "缓慢还原，避免借力弹动"],
    },
    # lower arms
    {
        "id": "local-wrist-curl",
        "name": "wrist curl",
        "bodyPart": "lower arms",
        "target": "forearms",
        "secondaryMuscles": [],
        "equipment": "dumbbell",
        "gifUrl": "https://v2.exercisedb.io/image/2mZQk7x9cYdKc1",
        "instructions": ["前臂放在大腿上，手心向上握哑铃", "只用腕部向上弯举", "缓慢下放到最低点", "保持肘部与前臂稳定不动"],
    },
    {
        "id": "local-reverse-wrist-curl",
        "name": "reverse wrist curl",
        "bodyPart": "lower arms",
        "target": "forearms",
        "secondaryMuscles": [],
        "equipment": "dumbbell",
        "gifUrl": "https://v2.exercisedb.io/image/7Kp1tQz3bVn0sA",
        "instructions": ["前臂放在大腿上，手心向下握哑铃", "只用腕部向上抬起", "缓慢下放", "避免肩肘参与发力"],
    },
]


def fetch_exercisedb(path: str, params: Optional[dict[str, Any]] = None) -> Any:
    try:
        with httpx.Client(timeout=20) as client:
            response = client.get(f"{EXERCISEDB_BASE}{path}", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        return {"fallback": True, "error": str(exc), "data": []}


def unwrap_response(payload: Any) -> Any:
    if isinstance(payload, dict):
        # oss v1 uses {success, meta, data:[...]} for list endpoints and {success, data:{...}} for detail.
        if "data" in payload:
            return payload.get("data")
        for key in ("data", "exercises", "results"):
            if key in payload:
                return payload[key]
    return payload


def normalize_exercise(item: dict[str, Any]) -> dict[str, Any]:
    # Support both legacy ExerciseDB-like fields and EDB V1 fields (oss.exercisedb.dev).
    body_parts = item.get("bodyParts") or item.get("body_parts") or []
    body_part = item.get("bodyPart") or item.get("body_part") or (body_parts[0] if isinstance(body_parts, list) and body_parts else "default")
    target_muscles = item.get("targetMuscles") or item.get("target_muscles") or []
    target = item.get("target") or (target_muscles[0] if isinstance(target_muscles, list) and target_muscles else "")
    secondary = item.get("secondaryMuscles") or item.get("secondary_muscles") or []
    equipments = item.get("equipments") or item.get("equipment") or "body weight"
    if isinstance(equipments, list):
        equipment = equipments[0] if equipments else "body weight"
    elif isinstance(equipments, str):
        equipment = equipments
    else:
        equipment = "body weight"
    difficulty = infer_difficulty(equipment, body_part)
    image_url = item.get("gifUrl") or item.get("image") or ""
    muscles = [target, *secondary] if target else (target_muscles if isinstance(target_muscles, list) else secondary)
    localized = localize_exercise_fields(
        name=item.get("name") or "unknown exercise",
        equipment=equipment,
        body_part=body_part,
        target=target,
        secondary=secondary if isinstance(secondary, list) else [],
        target_muscles=muscles if isinstance(muscles, list) else [],
        instructions=item.get("instructions") or [],
        difficulty=difficulty,
        standard_pose=STANDARD_POSE_TEMPLATES.get(body_part, STANDARD_POSE_TEMPLATES["default"]),
    )
    return {
        "id": str(item.get("id") or item.get("exerciseId") or item.get("name")),
        **localized,
        "common_errors": COMMON_ERRORS.get(body_part, COMMON_ERRORS.get("chest", [])),
        # Always proxy images through backend to avoid Electron direct-load edge cases,
        # and enable local disk cache for stable rendering in packaged apps.
        "image_url": build_proxy_image_url(image_url),
        "raw": item,
    }


def build_proxy_image_url(url: str) -> str:
    if not url:
        return ""
    return f"/api/exercises/proxy-image?url={quote(url, safe='')}"


def fetch_oss_filtered(body_part: str, limit: int, offset: int) -> list[dict[str, Any]]:
    """Fetch exercises from oss EDB V1 and filter by body part.

    EDB V1 doesn't provide a bodyPart filter endpoint in the free tier, so we page through
    `/exercises` and filter in-process. We cap pages to keep latency bounded.
    """
    need = max(0, offset) + max(1, limit)
    cursor: Optional[str] = None
    matched: list[dict[str, Any]] = []
    seen: set[str] = set()
    pages = 0
    # Pull up to ~8 pages * 50 = 400 raw rows max.
    while len(matched) < need and pages < 8:
        params: dict[str, Any] = {"limit": 50}
        if cursor:
            params["cursor"] = cursor
        payload = fetch_exercisedb("/exercises", params)
        rows = unwrap_response(payload)
        if not isinstance(rows, list) or not rows:
            break
        for item in rows:
            if not isinstance(item, dict):
                continue
            eid = str(item.get("exerciseId") or item.get("id") or "")
            if eid and eid in seen:
                continue
            parts = item.get("bodyParts") or []
            if isinstance(parts, list) and (body_part in parts):
                if eid:
                    seen.add(eid)
                matched.append(normalize_exercise(item))
        meta = payload.get("meta") if isinstance(payload, dict) else None
        cursor = meta.get("nextCursor") if isinstance(meta, dict) else None
        if not cursor:
            break
        pages += 1
    return matched[offset : offset + limit]

def fetch_legacy_list(body_part: str, limit: int, offset: int) -> list[dict[str, Any]]:
    payload = fetch_exercisedb(f"/exercises/bodyPart/{body_part}", {"limit": limit, "offset": offset})
    rows = unwrap_response(payload)
    if not isinstance(rows, list) or not rows:
        return []
    return [normalize_exercise(item) for item in rows if isinstance(item, dict)]


def local_exercises(body_part: str, limit: int, offset: int = 0) -> list[dict[str, Any]]:
    rows = [item for item in LOCAL_EXERCISES if item["bodyPart"] == body_part]
    if not rows:
        rows = LOCAL_EXERCISES
    return [normalize_exercise(item) for item in rows[offset : offset + limit]]


def infer_difficulty(equipment: str, body_part: str) -> str:
    if equipment in {"barbell", "smith machine", "weighted"}:
        return "advanced"
    if equipment in {"dumbbell", "cable", "kettlebell", "ez barbell"} or body_part == "back":
        return "intermediate"
    return "beginner"


def cache_get(redis: RedisDep, key: str) -> Any:
    cached = redis.get(key)
    if isinstance(cached, (str, bytes, bytearray)):
        return json.loads(cached)
    return None


def cache_set(redis: RedisDep, key: str, data: Any) -> None:
    redis.setex(key, 86400, json.dumps(data, ensure_ascii=False))


@router.get("")
@router.get("/list")
def list_exercises(
    redis: RedisDep,
    bodyPart: str = Query("chest"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    cache_key = f"exercises:list:{EXERCISE_CACHE_VERSION}:{EXERCISEDB_PROVIDER}:{bodyPart}:{limit}:{offset}"
    cached = cache_get(redis, cache_key)
    if cached is not None:
        return cached
    if EXERCISEDB_PROVIDER == "oss_v1":
        data = fetch_oss_filtered(bodyPart, limit, offset)
    else:
        data = fetch_legacy_list(bodyPart, limit, offset)
    if not data:
        data = local_exercises(bodyPart, limit, offset)
    cache_set(redis, cache_key, data)
    return data


@router.get("/bodyparts")
def body_parts(redis: RedisDep) -> list[str]:
    cache_key = "exercises:bodyparts"
    cached = cache_get(redis, cache_key)
    if cached is not None:
        return cached
    if EXERCISEDB_PROVIDER == "oss_v1":
        payload = fetch_exercisedb("/bodyparts")
        data = unwrap_response(payload)
        if isinstance(data, list):
            names: list[str] = []
            for item in data:
                if isinstance(item, dict) and item.get("name"):
                    names.append(str(item["name"]))
            if names:
                cache_set(redis, cache_key, names)
                return names
    else:
        payload = fetch_exercisedb("/exercises/bodyPartList")
        data = unwrap_response(payload)
        if isinstance(data, list) and data:
            cache_set(redis, cache_key, data)
            return data

    fallback = ["chest", "back", "waist", "upper legs", "shoulders", "upper arms"]
    cache_set(redis, cache_key, fallback)
    return fallback


@router.get("/proxy-image")
def proxy_image(url: str = Query(..., min_length=1)) -> Response:
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="图片地址不合法")
    try:
        _IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        # If cache dir creation fails, still attempt a direct fetch.
        pass

    cache_key = hashlib.md5(url.encode("utf-8")).hexdigest()
    cached_bytes_path = _IMAGE_CACHE_DIR / f"{cache_key}.bin"
    cached_meta_path = _IMAGE_CACHE_DIR / f"{cache_key}.json"

    if cached_bytes_path.exists() and cached_meta_path.exists():
        try:
            meta = json.loads(cached_meta_path.read_text("utf-8"))
            content_type = str(meta.get("content_type") or "image/gif")
            return Response(content=cached_bytes_path.read_bytes(), media_type=content_type)
        except OSError:
            # fall through to refetch
            pass
        except json.JSONDecodeError:
            # fall through to refetch
            pass
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://exercisedb.io/",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=404, detail=f"图片加载失败：{exc}") from exc

    content_type = response.headers.get("content-type", "image/gif")
    # Best-effort cache to disk for packaged/offline stability.
    try:
        tmp_bytes = cached_bytes_path.with_suffix(".bin.tmp")
        tmp_meta = cached_meta_path.with_suffix(".json.tmp")
        tmp_bytes.write_bytes(response.content)
        tmp_meta.write_text(json.dumps({"content_type": content_type}, ensure_ascii=False), "utf-8")
        tmp_bytes.replace(cached_bytes_path)
        tmp_meta.replace(cached_meta_path)
    except OSError:
        pass
    return Response(content=response.content, media_type=content_type)


@router.get("/{exercise_id}")
def get_exercise(exercise_id: str, redis: RedisDep) -> dict[str, Any]:
    cache_key = f"exercises:detail:{EXERCISE_CACHE_VERSION}:{EXERCISEDB_PROVIDER}:{exercise_id}"
    cached = cache_get(redis, cache_key)
    if cached is not None:
        return cached
    if EXERCISEDB_PROVIDER == "oss_v1":
        payload = fetch_exercisedb(f"/exercises/{exercise_id}")
    else:
        payload = fetch_exercisedb(f"/exercises/exercise/{exercise_id}")
    data = unwrap_response(payload)
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict) or not data:
        for item in LOCAL_EXERCISES:
            if item["id"] == exercise_id:
                normalized = normalize_exercise(item)
                cache_set(redis, cache_key, normalized)
                return normalized
        data = LOCAL_EXERCISES[0]
    normalized = normalize_exercise(data)
    cache_set(redis, cache_key, normalized)
    return normalized
