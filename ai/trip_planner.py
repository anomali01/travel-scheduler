# ai/trip_planner.py
"""
Orchestrator utama — Trip Planner.
Mengkoordinasikan semua modul AI untuk menghasilkan
rencana perjalanan lengkap end-to-end.

Alur:
  1. Parse input user (NLP)
  2. Resolve kota asal & tujuan → indonesia_db
  3. Cari penerbangan (Amadeus / lokal)
  4. Cari hotel (Google Places / OSM / lokal)
  5. Ambil cuaca (Open-Meteo, gratis)
  6. Fetch destinasi wisata (OSM Overpass)
  7. Generate itinerary harian (CSP Solver)
  8. Kalkulasi budget breakdown
  9. Gabungkan → TripPlan
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import pandas as pd

# ──────────────────────────────────────────────
# IMPORTS
# ──────────────────────────────────────────────
from data.indonesia_db import find_city, City, estimate_travel
from ai.nlp_parser      import TripRequest, parse_trip_request
from ai.flight_searcher import FlightSearchResult, search_flights
from ai.hotel_finder    import HotelSearchResult, find_hotels
from ai.weather_fetcher import WeatherForecast, get_weather_for_trip
from ai.budget_calculator import BudgetBreakdown, calculate_budget, suggest_hotel_tier
from ai.csp_solver      import solve, ScheduleResult
from data.osm_collector import fetch_wisata
from data.preprocessing import preprocess


# ──────────────────────────────────────────────
# DATA CLASS — OUTPUT UTAMA
# ──────────────────────────────────────────────

@dataclass
class DayPlan:
    day_number  : int
    date        : date
    schedule    : ScheduleResult
    weather     : Optional[object]   # DayWeather


@dataclass
class TripPlan:
    request      : TripRequest
    origin_city  : Optional[City]
    dest_city    : Optional[City]

    # Komponen
    flights      : Optional[FlightSearchResult]
    hotels       : Optional[HotelSearchResult]
    weather      : Optional[WeatherForecast]
    days         : list[DayPlan]
    budget       : Optional[BudgetBreakdown]

    # Meta
    hotel_tier   : str
    compute_ms   : float
    warnings     : list[str]
    tips         : list[str]

    # Status
    success      : bool
    error_msg    : str = ""


# ──────────────────────────────────────────────
# CACHE DATA WISATA (agar tidak fetch ulang)
# ──────────────────────────────────────────────

_wisata_cache: dict[str, pd.DataFrame] = {}


def _get_wisata(city: City, preferences: list[str]) -> pd.DataFrame:
    """Ambil data wisata dari cache atau fetch dari OSM."""
    city_key = city.name.lower()

    if city_key not in _wisata_cache:
        import os
        raw_path   = f"data/raw/wisata_{city_key}_raw.csv"
        clean_path = f"data/processed/wisata_{city_key}_clean.csv"

        os.makedirs("data/raw",       exist_ok=True)
        os.makedirs("data/processed", exist_ok=True)

        if os.path.exists(clean_path):
            df = pd.read_csv(clean_path)
            if not df.empty:
                _wisata_cache[city_key] = df
                return df

        # Fetch dari OSM
        df_raw = fetch_wisata(kota=city.name, save_path=raw_path)
        if not df_raw.empty:
            df = preprocess(raw_path, clean_path)
        else:
            df = _fallback_wisata(city)

        _wisata_cache[city_key] = df

    df = _wisata_cache[city_key].copy()

    # Filter berdasarkan preferensi
    PREF_TO_CATEGORY = {
        "Pantai"  : ["Pantai", "Wisata Alam"],
        "Budaya"  : ["Museum", "Wisata Umum", "Religi"],
        "Alam"    : ["Wisata Alam", "Taman"],
        "Kuliner" : ["Kuliner", "Restoran"],
        "Hiburan" : ["Hiburan", "Kebun Binatang"],
        "Religi"  : ["Religi"],
        "Taman"   : ["Taman"],
    }
    cats = []
    for pref in preferences:
        cats.extend(PREF_TO_CATEGORY.get(pref, []))

    if cats and "category" in df.columns:
        filtered = df[df["category"].isin(cats)]
        if not filtered.empty:
            return filtered

    return df


def _fallback_wisata(city: City) -> pd.DataFrame:
    """Data wisata dummy jika OSM tidak tersedia."""
    templates = {
        "bali": [
            {"name":"Tanah Lot","category":"Wisata Umum","lat":-8.6213,"lon":115.0863,
             "open_hour":7,"close_hour":19,"duration_min":90,"price_idr":60000,"rating":4.7},
            {"name":"Ubud Monkey Forest","category":"Wisata Alam","lat":-8.5188,"lon":115.2588,
             "open_hour":8,"close_hour":18,"duration_min":90,"price_idr":80000,"rating":4.5},
            {"name":"Pantai Kuta","category":"Pantai","lat":-8.7195,"lon":115.1686,
             "open_hour":6,"close_hour":22,"duration_min":120,"price_idr":0,"rating":4.3},
            {"name":"Tegallalang Rice Terrace","category":"Wisata Alam","lat":-8.4312,"lon":115.2778,
             "open_hour":7,"close_hour":18,"duration_min":90,"price_idr":50000,"rating":4.5},
            {"name":"Pura Besakih","category":"Religi","lat":-8.3739,"lon":115.4517,
             "open_hour":8,"close_hour":17,"duration_min":120,"price_idr":60000,"rating":4.6},
            {"name":"Seminyak Beach","category":"Pantai","lat":-8.6934,"lon":115.1602,
             "open_hour":6,"close_hour":22,"duration_min":120,"price_idr":0,"rating":4.4},
            {"name":"Museum Puri Lukisan","category":"Museum","lat":-8.5069,"lon":115.2641,
             "open_hour":9,"close_hour":17,"duration_min":90,"price_idr":75000,"rating":4.2},
            {"name":"Pantai Nusa Dua","category":"Pantai","lat":-8.8006,"lon":115.2314,
             "open_hour":6,"close_hour":20,"duration_min":120,"price_idr":0,"rating":4.5},
        ],
        "yogyakarta": [
            {"name":"Candi Borobudur","category":"Wisata Umum","lat":-7.6079,"lon":110.2038,
             "open_hour":6,"close_hour":17,"duration_min":180,"price_idr":50000,"rating":4.8},
            {"name":"Candi Prambanan","category":"Wisata Umum","lat":-7.7520,"lon":110.4914,
             "open_hour":6,"close_hour":17,"duration_min":150,"price_idr":40000,"rating":4.7},
            {"name":"Keraton Yogyakarta","category":"Museum","lat":-7.8052,"lon":110.3642,
             "open_hour":8,"close_hour":14,"duration_min":90,"price_idr":15000,"rating":4.4},
            {"name":"Malioboro","category":"Wisata Umum","lat":-7.7928,"lon":110.3660,
             "open_hour":8,"close_hour":22,"duration_min":120,"price_idr":0,"rating":4.5},
            {"name":"Pantai Parangtritis","category":"Pantai","lat":-8.0237,"lon":110.3317,
             "open_hour":6,"close_hour":18,"duration_min":120,"price_idr":5000,"rating":4.3},
            {"name":"Taman Sari","category":"Museum","lat":-7.8099,"lon":110.3595,
             "open_hour":9,"close_hour":15,"duration_min":90,"price_idr":15000,"rating":4.3},
        ],
        "lombok": [
            {"name":"Gili Trawangan","category":"Pantai","lat":-8.3503,"lon":116.0262,
             "open_hour":6,"close_hour":22,"duration_min":240,"price_idr":0,"rating":4.7},
            {"name":"Gunung Rinjani","category":"Wisata Alam","lat":-8.4124,"lon":116.4673,
             "open_hour":6,"close_hour":18,"duration_min":480,"price_idr":150000,"rating":4.8},
            {"name":"Pantai Selong Belanak","category":"Pantai","lat":-8.8637,"lon":116.2028,
             "open_hour":6,"close_hour":18,"duration_min":120,"price_idr":0,"rating":4.6},
            {"name":"Desa Sade","category":"Budaya","lat":-8.8484,"lon":116.2690,
             "open_hour":8,"close_hour":17,"duration_min":90,"price_idr":20000,"rating":4.3},
        ],
    }

    city_key = city.name.lower()
    data = templates.get(city_key, [
        {"name":f"Wisata {city.name} 1","category":"Wisata Umum",
         "lat":city.lat,"lon":city.lon,
         "open_hour":8,"close_hour":17,"duration_min":90,"price_idr":20000,"rating":4.0},
        {"name":f"Taman Kota {city.name}","category":"Taman",
         "lat":city.lat+0.01,"lon":city.lon+0.01,
         "open_hour":6,"close_hour":21,"duration_min":60,"price_idr":0,"rating":3.8},
        {"name":f"Museum {city.name}","category":"Museum",
         "lat":city.lat-0.01,"lon":city.lon-0.01,
         "open_hour":9,"close_hour":16,"duration_min":90,"price_idr":15000,"rating":4.0},
    ])

    df = pd.DataFrame(data)
    # Tambah kolom yang dibutuhkan CSP solver
    df["id"]             = range(len(df))
    df["duration_slot"]  = (df["duration_min"] / 30).astype(int).clip(lower=1)
    df["is_free"]        = (df["price_idr"] == 0).astype(int)
    df["source"]         = "fallback"
    return df


# ──────────────────────────────────────────────
# MAIN PLANNER
# ──────────────────────────────────────────────

def plan_trip(user_input: str,
              hotel_tier: str = "auto",
              time_limit_csp: float = 10.0) -> TripPlan:
    """
    Generate rencana perjalanan lengkap dari input natural language.

    Parameter
    ---------
    user_input     : Teks dari user ("Mau ke Bali 3 hari 5 juta 2 orang")
    hotel_tier     : "budget", "mid", "luxury", atau "auto" (otomatis berdasarkan budget)
    time_limit_csp : Batas waktu CSP solver per hari (detik)

    Return
    ------
    TripPlan berisi semua komponen perjalanan
    """
    t_start  = time.perf_counter()
    warnings = []
    tips     = []

    # ── 1. PARSE INPUT ──────────────────────────
    try:
        request = parse_trip_request(user_input)
    except Exception as e:
        return TripPlan(
            request=None, origin_city=None, dest_city=None,
            flights=None, hotels=None, weather=None, days=[],
            budget=None, hotel_tier="mid", compute_ms=0,
            warnings=[], tips=[], success=False,
            error_msg=f"Gagal memahami input: {e}"
        )

    # ── 2. RESOLVE KOTA ──────────────────────────
    origin_city = find_city(request.origin)
    dest_city   = find_city(request.destination)

    if not dest_city:
        warnings.append(f"⚠️ Kota tujuan '{request.destination}' tidak ditemukan. Menggunakan Bali.")
        dest_city = find_city("Bali")

    if not origin_city:
        warnings.append(f"⚠️ Kota asal '{request.origin}' tidak ditemukan. Menggunakan Jakarta.")
        origin_city = find_city("Jakarta")

    # ── 3. CARI PENERBANGAN ──────────────────────
    try:
        flights = search_flights(origin_city, dest_city, request.depart_date, request.num_people)
    except Exception as e:
        warnings.append(f"⚠️ Gagal cari penerbangan: {e}")
        flights = None

    # ── 4. TENTUKAN TIER HOTEL ───────────────────
    if hotel_tier == "auto":
        hotel_tier = suggest_hotel_tier(
            request.budget_per_person,
            dest_city.name,
            request.num_days
        )

    # ── 5. CARI HOTEL ────────────────────────────
    try:
        hotels = find_hotels(dest_city)
    except Exception as e:
        warnings.append(f"⚠️ Gagal cari hotel: {e}")
        hotels = None

    # ── 6. CUACA ─────────────────────────────────
    try:
        weather = get_weather_for_trip(
            dest_city.lat, dest_city.lon,
            dest_city.name,
            request.depart_date,
            request.num_days
        )
        if weather is None:
            tips.append("💡 Data cuaca tidak tersedia untuk tanggal tersebut (>16 hari ke depan).")
    except Exception as e:
        warnings.append(f"⚠️ Gagal ambil cuaca: {e}")
        weather = None

    # ── 7. DATA WISATA ───────────────────────────
    try:
        df_wisata = _get_wisata(dest_city, request.preferences)
    except Exception as e:
        warnings.append(f"⚠️ Gagal ambil data wisata: {e}")
        df_wisata = _fallback_wisata(dest_city)

    # ── 8. GENERATE ITINERARY HARIAN (CSP) ───────
    days = []
    daily_wisata_cost = 0
    visited_ids = set()

    for day_i in range(request.num_days):
        current_date = request.depart_date + timedelta(days=day_i)

        # Budget harian untuk wisata per orang
        daily_budget = request.budget_daily_per_person

        # Filter tempat yang sudah dikunjungi di hari sebelumnya
        df_wisata_day = df_wisata[~df_wisata["id"].isin(visited_ids)].reset_index(drop=True)
        if df_wisata_day.empty:
            visited_ids.clear()
            df_wisata_day = df_wisata.copy()

        # CSP solver untuk hari ini
        try:
            sched = solve(
                df_places  = df_wisata_day,
                budget     = daily_budget,
                max_hours  = 9,   # 9 jam wisata per hari
                start_hour = request.start_hour,
                categories = None,  # semua kategori
                time_limit = time_limit_csp,
            )
            # Fallback jika solve gagal tapi masih ada data asli (retry tanpa filter)
            if (not sched or not sched.success or sched.itinerary.empty) and not df_wisata.empty:
                sched = solve(
                    df_places  = df_wisata,
                    budget     = daily_budget,
                    max_hours  = 9,
                    start_hour = request.start_hour,
                    categories = None,
                    time_limit = time_limit_csp,
                )
        except Exception as e:
            warnings.append(f"⚠️ CSP Day {day_i+1} failed: {e}")
            sched = None

        # Ambil cuaca untuk hari ini
        day_weather = None
        if weather and weather.daily:
            for dw in weather.daily:
                if dw.date == current_date:
                    day_weather = dw
                    break

        days.append(DayPlan(
            day_number = day_i + 1,
            date       = current_date,
            schedule   = sched,
            weather    = day_weather,
        ))

        # Akumulasi biaya wisata dan track visited IDs
        if sched and sched.success and not sched.itinerary.empty:
            daily_wisata_cost = max(daily_wisata_cost, sched.total_cost)
            visited_ids.update(sched.itinerary["id"].tolist())

    # ── 9. KALKULASI BUDGET ───────────────────────
    if flights and hotels:
        try:
            budget = calculate_budget(
                request            = request,
                flights            = flights,
                hotels             = hotels,
                wisata_cost_per_day= daily_wisata_cost,
                hotel_tier         = hotel_tier,
            )
        except Exception as e:
            warnings.append(f"⚠️ Gagal kalkulasi budget: {e}")
            budget = None
    else:
        budget = None

    # ── 10. TIPS TAMBAHAN ─────────────────────────
    if budget and not budget.is_within_budget:
        deficit = abs(budget.surplus_deficit)
        tips.append(f"⚠️ Budget kurang Rp{deficit:,}. Pertimbangkan hotel budget atau kurangi hari.")
    elif budget and budget.surplus_deficit > 0:
        tips.append(f"✅ Budget cukup! Sisa Rp{budget.surplus_deficit:,} bisa untuk upgrade atau oleh-oleh lebih.")

    if dest_city.name.lower() in ["bali", "lombok", "raja ampat"]:
        tips.append("🌊 Bawa pakaian renang & sunscreen SPF 50+.")
    if dest_city.name.lower() in ["yogyakarta", "solo"]:
        tips.append("🛺 Sewa becak atau dokar untuk keliling kota tua lebih seru!")
    if dest_city.name.lower() in ["raja ampat", "labuan bajo"]:
        tips.append("🤿 Book paket diving/snorkeling jauh hari agar dapat harga terbaik.")

    elapsed = (time.perf_counter() - t_start) * 1000

    return TripPlan(
        request     = request,
        origin_city = origin_city,
        dest_city   = dest_city,
        flights     = flights,
        hotels      = hotels,
        weather     = weather,
        days        = days,
        budget      = budget,
        hotel_tier  = hotel_tier,
        compute_ms  = round(elapsed, 1),
        warnings    = warnings,
        tips        = tips,
        success     = True,
    )


def plan_trip_from_form(origin: str, destination: str,
                        depart_date: date, return_date: date,
                        num_people: int, budget_total: int,
                        preferences: list[str], start_hour: int = 8,
                        hotel_tier: str = "auto") -> TripPlan:
    """
    Entry point dari form input (non-NLP).
    Langsung terima parameter terstruktur dari form Streamlit.
    """
    from ai.nlp_parser import TripRequest
    num_days = max(1, (return_date - depart_date).days)

    request = TripRequest(
        origin           = origin,
        destination      = destination,
        depart_date      = depart_date,
        return_date      = return_date,
        num_days         = num_days,
        num_people       = num_people,
        budget_total     = budget_total,
        budget_per_person= budget_total // max(1, num_people),
        preferences      = preferences,
        start_hour       = start_hour,
        raw_input        = f"{origin} → {destination}, {num_days} hari, {num_people} orang",
    )

    # Simulasikan plan_trip tapi dengan request yang sudah terstruktur
    return _execute_plan(request, hotel_tier)


def _execute_plan(request: TripRequest, hotel_tier: str = "auto") -> TripPlan:
    """Internal: jalankan planning dengan TripRequest yang sudah terstruktur."""
    t_start  = time.perf_counter()
    warnings = []
    tips     = []

    origin_city = find_city(request.origin)
    dest_city   = find_city(request.destination)

    if not dest_city:
        warnings.append(f"Kota tujuan '{request.destination}' tidak dikenali. Menggunakan Bali.")
        dest_city = find_city("Bali")
    if not origin_city:
        warnings.append(f"Kota asal '{request.origin}' tidak dikenali. Menggunakan Jakarta.")
        origin_city = find_city("Jakarta")

    try:
        flights = search_flights(origin_city, dest_city, request.depart_date, request.num_people)
    except Exception as e:
        warnings.append(f"Flight search error: {e}")
        flights = None

    if hotel_tier == "auto":
        hotel_tier = suggest_hotel_tier(request.budget_per_person, dest_city.name, request.num_days)

    try:
        hotels = find_hotels(dest_city)
    except Exception as e:
        warnings.append(f"Hotel search error: {e}")
        hotels = None

    try:
        weather = get_weather_for_trip(
            dest_city.lat, dest_city.lon, dest_city.name,
            request.depart_date, request.num_days)
    except:
        weather = None

    try:
        df_wisata = _get_wisata(dest_city, request.preferences)
    except Exception as _we:
        warnings.append(f"Wisata fallback aktif: {_we}")
        df_wisata = _fallback_wisata(dest_city)

    days = []
    daily_wisata_cost = 0
    visited_ids = set()
    for day_i in range(request.num_days):
        current_date = request.depart_date + timedelta(days=day_i)
        
        # Filter tempat yang sudah dikunjungi di hari sebelumnya
        df_wisata_day = df_wisata[~df_wisata["id"].isin(visited_ids)].reset_index(drop=True)
        if df_wisata_day.empty:
            visited_ids.clear()
            df_wisata_day = df_wisata.copy()
            
        try:
            sched = solve(df_wisata_day, budget=request.budget_daily_per_person,
                          max_hours=9, start_hour=request.start_hour, time_limit=10.0)
            
            # Fallback jika solve gagal tapi masih ada data asli (retry tanpa filter)
            if (not sched or not sched.success or sched.itinerary.empty) and not df_wisata.empty:
                sched = solve(df_wisata, budget=request.budget_daily_per_person,
                              max_hours=9, start_hour=request.start_hour, time_limit=10.0)
        except Exception as _se:
            warnings.append(f"CSP Day {day_i+1} error: {_se}")
            sched = None

        day_weather = None
        if weather and weather.daily:
            for dw in weather.daily:
                if dw.date == current_date:
                    day_weather = dw
                    break

        days.append(DayPlan(day_i+1, current_date, sched, day_weather))
        if sched and sched.success and not sched.itinerary.empty:
            daily_wisata_cost = max(daily_wisata_cost, sched.total_cost)
            visited_ids.update(sched.itinerary["id"].tolist())

    try:
        budget = calculate_budget(request, flights, hotels, daily_wisata_cost, hotel_tier) if (flights and hotels) else None
    except Exception as _be:
        warnings.append(f"Budget calc error: {_be}")
        budget = None

    if budget and not budget.is_within_budget:
        tips.append(f"⚠️ Budget kurang Rp{abs(budget.surplus_deficit):,}.")
    elif budget and budget.surplus_deficit > 0:
        tips.append(f"✅ Budget cukup! Sisa Rp{budget.surplus_deficit:,}.")

    elapsed = (time.perf_counter() - t_start) * 1000
    return TripPlan(
        request=request, origin_city=origin_city, dest_city=dest_city,
        flights=flights, hotels=hotels, weather=weather, days=days,
        budget=budget, hotel_tier=hotel_tier,
        compute_ms=round(elapsed, 1), warnings=warnings, tips=tips, success=True,
    )
