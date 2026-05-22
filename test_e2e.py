"""
End-to-end test: simulasi perencanaan trip Jakarta → Bali.
Verifikasi semua komponen berjalan tanpa error.
"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta

print("=" * 55)
print("  TravelAI Indonesia — End-to-End Test")
print("=" * 55)

# ── TEST 1: indonesia_db ──────────────────────────────────────
print("\n[1] Database lookup...")
from data.indonesia_db import find_city, estimate_travel, get_all_city_names, get_popular_destinations

bali    = find_city("Bali")
jakarta = find_city("Jakarta")
jogja   = find_city("Jogja")
lombok  = find_city("Lombok")

assert bali    is not None, "Bali not found"
assert jakarta is not None, "Jakarta not found"
assert jogja   is not None, "Jogja not found"
assert lombok  is not None, "Lombok not found"
assert bali.airport is not None, "Bali has no airport"
assert jakarta.airport.iata == "CGK", "Jakarta IATA wrong"

travel = estimate_travel(jakarta, bali)
assert travel["mode"] == "pesawat", f"Mode wrong: {travel['mode']}"
assert travel["price_min"] > 0
assert travel["duration_min"] > 0

cities = get_all_city_names()
assert len(cities) > 40, f"Too few cities: {len(cities)}"

print(f"  OK: {len(cities)} kota, Jakarta->Bali {travel['duration_min']}mnt, Rp{travel['price_min']:,}")

# ── TEST 2: NLP Parser ────────────────────────────────────────
print("\n[2] NLP Parser (rule-based)...")
from ai.nlp_parser import parse_trip_request

req = parse_trip_request("Mau ke Bali dari Jakarta, 3 orang, 5 hari, budget 15 juta, suka pantai")
assert req.destination.lower() in ["bali", "denpasar"], f"Dest: {req.destination}"
assert req.num_people == 3, f"People: {req.num_people}"
assert req.num_days == 5, f"Days: {req.num_days}"
assert req.budget_total == 15_000_000, f"Budget: {req.budget_total}"
assert "Pantai" in req.preferences, f"Prefs: {req.preferences}"
print(f"  OK: {req.origin} -> {req.destination}, {req.num_people} org, {req.num_days} hari, Rp{req.budget_total:,}")

# Test berbagai format input
r2 = parse_trip_request("Liburan ke Raja Ampat bertiga seminggu budget 20jt")
assert "raja" in r2.destination.lower() or "ampat" in r2.destination.lower(), f"Dest: {r2.destination}"
assert r2.num_people == 3
assert r2.num_days == 7
assert r2.budget_total == 20_000_000
print(f"  OK: Raja Ampat test: {r2.destination}, {r2.num_people} org, {r2.num_days} hr")

r3 = parse_trip_request("Trip ke Yogyakarta berdua 3 malam")
assert r3.num_people == 2
assert r3.num_days == 3
print(f"  OK: Jogja test: {r3.destination}, {r3.num_people} org, {r3.num_days} malam")

# ── TEST 3: Weather Fetcher ───────────────────────────────────
print("\n[3] Weather fetcher (Open-Meteo)...")
from ai.weather_fetcher import fetch_weather

weather = fetch_weather(bali.lat, bali.lon, "Bali", num_days=3)
if weather:
    assert len(weather.daily) > 0
    dw = weather.daily[0]
    assert 20 <= dw.temp_max <= 40, f"Temp range invalid: {dw.temp_max}"
    assert 0 <= dw.activity_score <= 100
    print(f"  OK: {len(weather.daily)} hari, {dw.description}, skor {dw.activity_score}")
else:
    print("  SKIP: Weather API unreachable (network issue)")

# ── TEST 4: Flight Searcher ───────────────────────────────────
print("\n[4] Flight searcher (local estimate)...")
from ai.flight_searcher import search_flights

depart_date = date.today() + timedelta(days=14)
flights = search_flights(jakarta, bali, depart_date, num_people=3)
assert flights is not None
assert len(flights.options) > 0
assert flights.cheapest_price > 0
cheapest = flights.options[0]
print(f"  OK: {len(flights.options)} opsi, termurah Rp{flights.cheapest_price:,} ({cheapest.airline})")

# ── TEST 5: Hotel Finder ──────────────────────────────────────
print("\n[5] Hotel finder (OSM/local)...")
from ai.hotel_finder import find_hotels

hotels = find_hotels(bali)
assert hotels is not None
assert len(hotels.budget) > 0
assert len(hotels.mid)    > 0
assert len(hotels.luxury) > 0
print(f"  OK: {len(hotels.budget)} budget, {len(hotels.mid)} mid, {len(hotels.luxury)} luxury")
print(f"  Sample: {hotels.mid[0].name} - Rp{hotels.mid[0].price_per_night:,}/malam")

# ── TEST 6: CSP Solver ───────────────────────────────────────
print("\n[6] CSP Solver...")
from ai.csp_solver import solve
import pandas as pd

df_dummy = pd.DataFrame([
    {"id":0,"name":"Tanah Lot","category":"Wisata Umum","lat":-8.621,"lon":115.086,
     "open_hour":7,"close_hour":19,"duration_min":90,"price_idr":60000,"rating":4.7,
     "duration_slot":3,"is_free":0,"source":"test"},
    {"id":1,"name":"Ubud Forest","category":"Wisata Alam","lat":-8.518,"lon":115.258,
     "open_hour":8,"close_hour":18,"duration_min":90,"price_idr":80000,"rating":4.5,
     "duration_slot":3,"is_free":0,"source":"test"},
    {"id":2,"name":"Pantai Kuta","category":"Pantai","lat":-8.719,"lon":115.168,
     "open_hour":6,"close_hour":22,"duration_min":120,"price_idr":0,"rating":4.3,
     "duration_slot":4,"is_free":1,"source":"test"},
    {"id":3,"name":"Tegallalang","category":"Wisata Alam","lat":-8.431,"lon":115.277,
     "open_hour":7,"close_hour":18,"duration_min":90,"price_idr":50000,"rating":4.5,
     "duration_slot":3,"is_free":0,"source":"test"},
])

result = solve(df_dummy, budget=200_000, max_hours=8, start_hour=8, time_limit=5.0)
assert result.success, f"CSP failed: {result.message}"
assert len(result.itinerary) > 0
assert result.conflicts == 0, f"Conflicts: {result.conflicts}"
print(f"  OK: {len(result.itinerary)} tempat, biaya Rp{result.total_cost:,}, konflik={result.conflicts}, {result.solve_time_ms:.0f}ms")

# ── TEST 7: Budget Calculator ─────────────────────────────────
print("\n[7] Budget calculator...")
from ai.budget_calculator import calculate_budget
from ai.nlp_parser import TripRequest

req_full = TripRequest(
    origin="Jakarta", destination="Bali",
    depart_date=depart_date, return_date=depart_date+timedelta(days=4),
    num_days=4, num_people=3,
    budget_total=15_000_000, budget_per_person=5_000_000,
    preferences=["Pantai","Budaya"], start_hour=8, raw_input="test"
)

budget = calculate_budget(req_full, flights, hotels, wisata_cost_per_day=100_000, hotel_tier="mid")
assert budget.grand_total > 0
assert budget.transport_go > 0
assert budget.hotel_total > 0
assert len(budget.items) > 0
print(f"  OK: Total Rp{budget.grand_total:,}, {'dalam' if budget.is_within_budget else 'melebihi'} budget")
print(f"  Transport: Rp{budget.transport_go:,} | Hotel: Rp{budget.hotel_total:,} | Surplus: Rp{budget.surplus_deficit:,}")

# ── TEST 8: Trip Planner (Full E2E) ──────────────────────────
print("\n[8] Trip Planner full orchestration...")
from ai.trip_planner import plan_trip_from_form

plan = plan_trip_from_form(
    origin="Jakarta", destination="Bali",
    depart_date=depart_date,
    return_date=depart_date + timedelta(days=3),
    num_people=2, budget_total=10_000_000,
    preferences=["Pantai","Budaya"],
    start_hour=8, hotel_tier="mid"
)

assert plan.success, f"Plan failed: {plan.error_msg}"
assert plan.dest_city is not None
assert plan.flights   is not None
assert plan.hotels    is not None
assert len(plan.days) == 3
assert all(d.schedule is not None for d in plan.days)
print(f"  OK: {plan.request.origin} -> {plan.dest_city.name}")
print(f"  Days: {len(plan.days)} | Hotel tier: {plan.hotel_tier} | Time: {plan.compute_ms:.0f}ms")
if plan.budget:
    print(f"  Budget: Rp{plan.budget.grand_total:,} / Rp{plan.budget.budget_total:,}")
if plan.warnings:
    for w in plan.warnings:
        print(f"  WARN: {w}")

# ── SUMMARY ──────────────────────────────────────────────────
print("\n" + "=" * 55)
print("  ALL TESTS PASSED!")
print("=" * 55)
print(f"\n  App ready at: http://localhost:8501\n")
