"""Quick import test untuk semua module baru."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))

errors = []

def test(name, fn):
    try:
        fn()
        print(f"  ✅ {name}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        errors.append((name, str(e)))

print("\n🔍 Testing imports...\n")

test("data.indonesia_db",     lambda: __import__("data.indonesia_db", fromlist=["find_city"]))
test("data.preprocessing",   lambda: __import__("data.preprocessing", fromlist=["preprocess"]))
test("data.osm_collector",   lambda: __import__("data.osm_collector", fromlist=["fetch_wisata"]))
test("ai.csp_solver",        lambda: __import__("ai.csp_solver", fromlist=["solve"]))
test("ai.nlp_parser",        lambda: __import__("ai.nlp_parser", fromlist=["parse_trip_request"]))
test("ai.weather_fetcher",   lambda: __import__("ai.weather_fetcher", fromlist=["fetch_weather"]))
test("ai.flight_searcher",   lambda: __import__("ai.flight_searcher", fromlist=["search_flights"]))
test("ai.hotel_finder",      lambda: __import__("ai.hotel_finder", fromlist=["find_hotels"]))
test("ai.budget_calculator", lambda: __import__("ai.budget_calculator", fromlist=["calculate_budget"]))
test("ai.trip_planner",      lambda: __import__("ai.trip_planner", fromlist=["plan_trip_from_form"]))
test("utils.formatter",      lambda: __import__("utils.formatter", fromlist=["fmt_rp"]))
test("utils.map_utils",      lambda: __import__("utils.map_utils", fromlist=["make_itinerary_map"]))

print(f"\n{'='*40}")
if not errors:
    print("🎉 Semua module berhasil diimport!\n")
else:
    print(f"⚠️  {len(errors)} error ditemukan:\n")
    for name, err in errors:
        print(f"  - {name}: {err}")
print()
