from __future__ import annotations

import re
from typing import Any

import requests

_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_WEATHER_CODE_ZH: dict[int, str] = {
    0: "晴朗",
    1: "大部晴朗",
    2: "多云",
    3: "阴天",
    45: "有雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "大毛毛雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "大阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷阵雨",
    96: "雷阵雨伴冰雹",
    99: "强雷阵雨伴冰雹",
}

_COMMON_CITIES = [
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "南京",
    "成都",
    "重庆",
    "武汉",
    "西安",
    "天津",
    "苏州",
    "郑州",
    "长沙",
    "青岛",
    "厦门",
    "大连",
    "沈阳",
    "哈尔滨",
    "昆明",
    "贵阳",
    "南宁",
    "海口",
    "三亚",
    "拉萨",
    "乌鲁木齐",
    "呼和浩特",
    "石家庄",
    "济南",
    "合肥",
    "福州",
    "南昌",
    "长春",
    "香港",
    "澳门",
    "台北",
]


def is_weather_question(question: str) -> bool:
    q = (question or "").strip()
    if not q:
        return False
    keywords = ["天气", "气温", "温度", "下雨", "下雪", "刮风", "预报", "多少度", "几度", "冷不冷", "热不热"]
    return any(k in q for k in keywords)


_TIME_WORDS = ("现在", "今天", "今日", "明日", "明天", "后天")


def _normalize_city_name(city: str) -> str:
    name = (city or "").strip()
    for suffix in ("市", "县", "区", "州", "盟", "旗"):
        if name.endswith(suffix) and len(name) > len(suffix):
            name = name[: -len(suffix)]
    for word in _TIME_WORDS:
        if name.endswith(word) and len(name) > len(word):
            name = name[: -len(word)]
    return name.strip()


def extract_city_from_question(question: str) -> str | None:
    q = (question or "").strip()
    patterns = [
        # 城市与时间词分开匹配，避免把「北京今天」整体当成城市名
        rf"([一-龥]{{2,8}}(?:市|县|区|州|盟|旗)?)(?:{'|'.join(_TIME_WORDS)})(?:的)?(?:天气|气温|温度)",
        rf"(?:{'|'.join(_TIME_WORDS)})(?:的)?([一-龥]{{2,8}}(?:市|县|区|州|盟|旗)?)(?:的)?(?:天气|气温|温度)",
        r"([一-龥]{2,8}(?:市|县|区|州|盟|旗)?)(?:的)?(?:天气|气温|温度)",
        r"(?:天气|气温|温度)(?:怎么样|如何|怎样|好不好).*?([一-龥]{2,8}(?:市|县|区)?)",
        rf"([一-龥]{{2,8}}(?:市|县|区)?)(?:{'|'.join(_TIME_WORDS)})?(?:多少度|几度)",
    ]
    for pattern in patterns:
        match = re.search(pattern, q)
        if match:
            city = _normalize_city_name(match.group(1))
            if city:
                return city
    for city in _COMMON_CITIES:
        if city in q:
            return city
    return None


def _weather_desc(code: int | None) -> str:
    if code is None:
        return "未知"
    return _WEATHER_CODE_ZH.get(int(code), "多变")


def _geocode_city(city: str) -> dict[str, Any] | None:
    response = requests.get(
        _GEO_URL,
        params={"name": city, "count": 5, "language": "zh", "format": "json"},
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results") or []
    if not results:
        return None

    normalized = city.replace("市", "")
    for item in results:
        name = str(item.get("name") or "")
        admin1 = str(item.get("admin1") or "")
        if normalized in name or normalized in admin1 or name.startswith(normalized):
            return item
    return results[0]


def fetch_weather(city: str) -> dict[str, Any]:
    location = _geocode_city(city)
    if not location:
        raise ValueError(f"未找到城市：{city}")

    latitude = location["latitude"]
    longitude = location["longitude"]
    timezone = location.get("timezone") or "Asia/Shanghai"

    response = requests.get(
        _FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
            "timezone": timezone,
            "forecast_days": 2,
        },
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    observed_at = current.get("time") or ""

    return {
        "city": str(location.get("name") or city),
        "region": str(location.get("admin1") or ""),
        "country": str(location.get("country") or ""),
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "observed_at": observed_at,
        "current": {
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "precipitation_mm": current.get("precipitation"),
            "weather_code": current.get("weather_code"),
            "weather_desc": _weather_desc(current.get("weather_code")),
        },
        "today": {
            "date": (daily.get("time") or [None])[0],
            "temp_max_c": (daily.get("temperature_2m_max") or [None])[0],
            "temp_min_c": (daily.get("temperature_2m_min") or [None])[0],
            "precipitation_probability_pct": (daily.get("precipitation_probability_max") or [None])[0],
            "precipitation_sum_mm": (daily.get("precipitation_sum") or [None])[0],
            "weather_code": (daily.get("weather_code") or [None])[0],
            "weather_desc": _weather_desc((daily.get("weather_code") or [None])[0]),
        },
        "tomorrow": {
            "date": (daily.get("time") or [None, None])[1],
            "temp_max_c": (daily.get("temperature_2m_max") or [None, None])[1],
            "temp_min_c": (daily.get("temperature_2m_min") or [None, None])[1],
            "precipitation_probability_pct": (daily.get("precipitation_probability_max") or [None, None])[1],
            "precipitation_sum_mm": (daily.get("precipitation_sum") or [None, None])[1],
            "weather_code": (daily.get("weather_code") or [None, None])[1],
            "weather_desc": _weather_desc((daily.get("weather_code") or [None, None])[1]),
        },
        "source": "Open-Meteo",
    }


def format_weather_answer(question: str, weather: dict[str, Any]) -> str:
    city = weather.get("city") or extract_city_from_question(question) or "当地"
    region = weather.get("region") or ""
    current = weather.get("current") or {}
    today = weather.get("today") or {}
    tomorrow = weather.get("tomorrow") or {}
    observed_at = str(weather.get("observed_at") or "")

    place = f"{region}{city}" if region and region not in city else city
    temp = current.get("temperature_c")
    feels = current.get("feels_like_c")
    humidity = current.get("humidity_pct")
    wind = current.get("wind_speed_kmh")
    precip = current.get("precipitation_mm")
    desc = current.get("weather_desc") or "未知"

    lines = [
        "一、实时天气",
        (
            f"{place}（观测时间 {observed_at}）：{desc}，气温 {temp}°C，"
            f"体感 {feels}°C，相对湿度 {humidity}%，风速 {wind} km/h，"
            f"当前降水 {precip if precip is not None else 0} mm。"
        ),
        "",
        "二、今明预报",
        (
            f"- 今日（{today.get('date') or '今天'}）：{today.get('weather_desc')}，"
            f"最高 {today.get('temp_max_c')}°C / 最低 {today.get('temp_min_c')}°C，"
            f"降水概率 {today.get('precipitation_probability_pct') or 0}%"
        ),
        (
            f"- 明日（{tomorrow.get('date') or '明天'}）：{tomorrow.get('weather_desc')}，"
            f"最高 {tomorrow.get('temp_max_c')}°C / 最低 {tomorrow.get('temp_min_c')}°C，"
            f"降水概率 {tomorrow.get('precipitation_probability_pct') or 0}%"
        ),
        "",
        "三、出行建议",
    ]

    code = int(current.get("weather_code") or 0)
    if code in {61, 63, 65, 80, 81, 82, 95, 96, 99} or (today.get("precipitation_probability_pct") or 0) >= 50:
        lines.append("- 可能有降雨，出门请带伞，注意路面湿滑。")
    elif code in {71, 73, 75, 85, 86}:
        lines.append("- 可能有降雪，注意保暖和出行安全。")
    elif (temp is not None and float(temp) >= 33) or (today.get("temp_max_c") is not None and float(today.get("temp_max_c")) >= 33):
        lines.append("- 气温偏高，注意防暑补水，避免正午高强度户外运动。")
    elif temp is not None and float(temp) <= 5:
        lines.append("- 气温偏低，注意添衣保暖。")
    else:
        lines.append("- 天气总体适宜日常活动，户外运动前可先热身。")

    lines.append(f"- 数据来源：{weather.get('source') or 'Open-Meteo'}（免费气象接口）。")
    return "\n".join(lines)


def answer_weather_question(question: str) -> tuple[str, dict[str, Any] | None]:
    city = extract_city_from_question(question)
    if not city:
        return (
            "一、直接回答\n"
            "请告诉我具体城市，例如“北京天气怎么样”或“上海今天气温多少”。\n\n"
            "二、详细说明\n"
            "- 需要城市名称才能查询实时天气\n"
            "- 支持全国主要城市",
            None,
        )
    weather = fetch_weather(city)
    return format_weather_answer(question, weather), weather
