# ai/weather_fetcher.py
"""
Fetcher cuaca menggunakan Open-Meteo API.
Sepenuhnya GRATIS — tidak memerlukan API key.
Dokumentasi: https://open-meteo.com/

Fitur:
  - Prakiraan cuaca 16 hari ke depan
  - Data per jam & harian
  - Indeks UV, presipitasi, kecepatan angin
  - Rekomendasi aktivitas berdasarkan cuaca
"""

from __future__ import annotations

import requests
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

# ──────────────────────────────────────────────
# API CONFIG
# ──────────────────────────────────────────────

OPEN_METEO_URL  = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SEC     = 10

# ──────────────────────────────────────────────
# DATA CLASS
# ──────────────────────────────────────────────

@dataclass
class DayWeather:
    date          : date
    temp_max      : float    # °C
    temp_min      : float    # °C
    precipitation : float    # mm
    uv_index      : float
    wind_speed    : float    # km/h
    weather_code  : int
    description   : str
    icon          : str
    activity_score: int      # 0-100 (skor kenyamanan wisata)
    tips          : str


@dataclass
class WeatherForecast:
    city_name   : str
    lat         : float
    lon         : float
    timezone    : str
    daily       : list[DayWeather]
    overall_tip : str


# ──────────────────────────────────────────────
# WMO WEATHER CODE MAPPING
# ──────────────────────────────────────────────

WMO_CODES = {
    0  : ("Cerah", "☀️"),
    1  : ("Mostly Clear", "🌤️"),
    2  : ("Sebagian Berawan", "⛅"),
    3  : ("Berawan", "☁️"),
    45 : ("Berkabut", "🌫️"),
    48 : ("Berkabut Beku", "🌫️"),
    51 : ("Gerimis Ringan", "🌦️"),
    53 : ("Gerimis Sedang", "🌦️"),
    55 : ("Gerimis Lebat", "🌧️"),
    61 : ("Hujan Ringan", "🌧️"),
    63 : ("Hujan Sedang", "🌧️"),
    65 : ("Hujan Lebat", "🌧️"),
    71 : ("Salju Ringan", "🌨️"),
    80 : ("Hujan Lokal", "🌦️"),
    81 : ("Hujan Lokal Sedang", "🌧️"),
    82 : ("Hujan Lokal Lebat", "⛈️"),
    95 : ("Petir", "⛈️"),
    96 : ("Petir + Hujan Es", "⛈️"),
    99 : ("Badai Petir", "🌩️"),
}


def _wmo_to_desc(code: int) -> tuple[str, str]:
    """Konversi WMO code → (deskripsi, emoji)."""
    return WMO_CODES.get(code, ("Tidak diketahui", "🌡️"))


def _calc_activity_score(code: int, uv: float, wind: float, precip: float) -> tuple[int, str]:
    """
    Hitung skor kenyamanan wisata (0–100) dan tips berdasarkan cuaca.
    """
    score = 100

    # Pengurangan berdasarkan cuaca
    if code >= 95:    score -= 60
    elif code >= 80:  score -= 40
    elif code >= 61:  score -= 30
    elif code >= 51:  score -= 15
    elif code >= 45:  score -= 10
    elif code >= 2:   score -= 5

    # UV index
    if uv >= 9:    score -= 15
    elif uv >= 7:  score -= 8
    elif uv >= 5:  score -= 3

    # Angin kencang
    if wind >= 50:   score -= 20
    elif wind >= 30: score -= 10
    elif wind >= 20: score -= 5

    # Presipitasi
    if precip >= 20:   score -= 15
    elif precip >= 10: score -= 8
    elif precip >= 5:  score -= 3

    score = max(0, min(100, score))

    # Tips berdasarkan skor
    if score >= 80:
        tip = "✅ Cuaca sangat ideal untuk wisata outdoor!"
    elif score >= 60:
        tip = "🟡 Cuaca cukup baik, bawa jaket & sunscreen."
    elif score >= 40:
        tip = "🟠 Cuaca kurang ideal, prioritaskan destinasi indoor."
    elif score >= 20:
        tip = "🔴 Cuaca buruk, pertimbangkan aktivitas indoor saja."
    else:
        tip = "⛔ Cuaca sangat buruk, tunda aktivitas outdoor."

    return score, tip


# ──────────────────────────────────────────────
# FETCHER UTAMA
# ──────────────────────────────────────────────

def fetch_weather(lat: float, lon: float,
                  city_name: str = "Destinasi",
                  num_days: int = 7) -> Optional[WeatherForecast]:
    """
    Ambil prakiraan cuaca dari Open-Meteo (gratis, no key).

    Parameter
    ---------
    lat, lon   : koordinat GPS kota tujuan
    city_name  : nama kota (untuk display)
    num_days   : jumlah hari prakiraan (max 16)

    Return
    ------
    WeatherForecast | None
    """
    num_days = min(num_days, 16)

    params = {
        "latitude"       : lat,
        "longitude"      : lon,
        "daily"          : [
            "weathercode",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "uv_index_max",
            "windspeed_10m_max",
        ],
        "timezone"       : "Asia/Jakarta",
        "forecast_days"  : num_days,
    }

    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=TIMEOUT_SEC)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"⚠️  Weather fetch failed: {e}")
        return None

    daily_data = data.get("daily", {})
    dates      = daily_data.get("time", [])
    codes      = daily_data.get("weathercode", [])
    temp_max   = daily_data.get("temperature_2m_max", [])
    temp_min   = daily_data.get("temperature_2m_min", [])
    precip     = daily_data.get("precipitation_sum", [])
    uv         = daily_data.get("uv_index_max", [])
    wind       = daily_data.get("windspeed_10m_max", [])

    daily_list = []
    for i, d in enumerate(dates):
        code  = codes[i] if i < len(codes) else 0
        desc, icon = _wmo_to_desc(code)
        uv_val  = uv[i]   if i < len(uv)    else 5.0
        wnd_val = wind[i] if i < len(wind)  else 10.0
        prp_val = precip[i] if i < len(precip) else 0.0
        score, tips = _calc_activity_score(code, uv_val, wnd_val, prp_val)

        daily_list.append(DayWeather(
            date          = date.fromisoformat(d),
            temp_max      = temp_max[i] if i < len(temp_max) else 30.0,
            temp_min      = temp_min[i] if i < len(temp_min) else 25.0,
            precipitation = prp_val,
            uv_index      = uv_val,
            wind_speed    = wnd_val,
            weather_code  = code,
            description   = desc,
            icon          = icon,
            activity_score= score,
            tips          = tips,
        ))

    # Tip keseluruhan berdasarkan rata-rata skor
    if daily_list:
        avg_score = sum(d.activity_score for d in daily_list) / len(daily_list)
        if avg_score >= 75:
            overall = f"🌟 Cuaca di {city_name} sangat bagus untuk liburan!"
        elif avg_score >= 55:
            overall = f"☀️ Cuaca di {city_name} cukup baik, siapkan perlengkapan hujan."
        elif avg_score >= 35:
            overall = f"🌧️ Cuaca di {city_name} kurang mendukung, pertimbangkan jadwal fleksibel."
        else:
            overall = f"⛈️ Cuaca di {city_name} buruk. Pertimbangkan untuk mengubah jadwal."
    else:
        overall = "Data cuaca tidak tersedia."

    return WeatherForecast(
        city_name   = city_name,
        lat         = lat,
        lon         = lon,
        timezone    = data.get("timezone", "Asia/Jakarta"),
        daily       = daily_list,
        overall_tip = overall,
    )


def get_weather_for_trip(lat: float, lon: float,
                         city_name: str,
                         depart_date: date,
                         num_days: int) -> Optional[WeatherForecast]:
    """
    Wrapper: ambil cuaca sesuai tanggal trip (bukan dari hari ini).
    Open-Meteo hanya bisa forecast 16 hari ke depan.
    Jika trip lebih dari 16 hari ke depan, return None.
    """
    from datetime import date as _date
    today = _date.today()
    days_until = (depart_date - today).days

    if days_until > 15:
        # Terlalu jauh, Open-Meteo tidak bisa forecast sejauh itu
        return None

    # Hitung berapa hari yang perlu diambil
    total_days = days_until + num_days
    forecast = fetch_weather(lat, lon, city_name, num_days=min(total_days, 16))

    if forecast is None:
        return None

    # Filter hanya tanggal yang relevan untuk trip
    trip_days = [
        d for d in forecast.daily
        if depart_date <= d.date <= depart_date + timedelta(days=num_days)
    ]
    forecast.daily = trip_days
    return forecast
