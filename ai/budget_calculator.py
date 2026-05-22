# ai/budget_calculator.py
"""
Kalkulator budget perjalanan lengkap.
Menghasilkan breakdown biaya detail per kategori
dan perbandingan dengan budget user.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ai.flight_searcher import FlightSearchResult
from ai.hotel_finder import HotelSearchResult, Hotel
from ai.nlp_parser import TripRequest

# ──────────────────────────────────────────────
# DATA CLASSES
# ──────────────────────────────────────────────

@dataclass
class BudgetItem:
    category : str
    label    : str
    amount   : int      # Rp
    per_unit : str      # "/orang", "/malam", "/hari", dll.
    quantity : int
    subtotal : int
    icon     : str


@dataclass
class BudgetBreakdown:
    # Tiket transport (PP per orang)
    transport_go     : int = 0
    transport_return : int = 0
    # Akomodasi
    hotel_per_night  : int = 0
    hotel_total      : int = 0
    # Wisata (tiket masuk)
    wisata_daily     : int = 0
    wisata_total     : int = 0
    # Makan & minum
    meals_daily      : int = 0
    meals_total      : int = 0
    # Transport lokal
    local_transport  : int = 0
    # Oleh-oleh & shopping
    souvenir         : int = 0
    # Darurat / cadangan
    emergency        : int = 0

    # Total
    grand_total      : int = 0
    budget_total     : int = 0
    is_within_budget : bool = True
    surplus_deficit  : int = 0  # positif = sisa, negatif = kurang

    # Items detail (untuk tabel)
    items            : list[BudgetItem] = field(default_factory=list)

    # Tier hotel yang digunakan
    hotel_tier       : str = "mid"


# ──────────────────────────────────────────────
# ESTIMASI BIAYA MAKAN PER HARI (Rp/orang)
# ──────────────────────────────────────────────

MEAL_COST_ESTIMATE = {
    "bali"       : {"budget": 80_000, "mid": 150_000, "luxury": 300_000},
    "jakarta"    : {"budget": 80_000, "mid": 150_000, "luxury": 350_000},
    "yogyakarta" : {"budget": 60_000, "mid": 100_000, "luxury": 250_000},
    "surabaya"   : {"budget": 70_000, "mid": 120_000, "luxury": 280_000},
    "lombok"     : {"budget": 70_000, "mid": 130_000, "luxury": 280_000},
    "default"    : {"budget": 60_000, "mid": 100_000, "luxury": 250_000},
}

LOCAL_TRANSPORT_ESTIMATE = {
    "bali"       : 100_000,  # sewa motor/ojek per hari
    "jakarta"    : 80_000,   # gojek/grabbike per hari
    "yogyakarta" : 60_000,
    "default"    : 75_000,
}

SOUVENIR_RATIO = 0.05  # 5% dari total budget untuk oleh-oleh
EMERGENCY_RATIO = 0.10  # 10% cadangan


def calculate_budget(request: TripRequest,
                     flights: FlightSearchResult,
                     hotels: HotelSearchResult,
                     wisata_cost_per_day: int,
                     hotel_tier: str = "mid") -> BudgetBreakdown:
    """
    Hitung breakdown budget lengkap.

    Parameter
    ---------
    request          : TripRequest dari user
    flights          : hasil pencarian penerbangan
    hotels           : hasil pencarian hotel
    wisata_cost_per_day: estimasi biaya tiket wisata per orang per hari (dari CSP)
    hotel_tier       : "budget", "mid", atau "luxury"
    """
    n      = request.num_people
    days   = request.num_days
    city   = request.destination.lower()

    # ── TRANSPORT ────────────────────────────
    cheapest_flight = flights.cheapest_price if flights.options else 0
    transport_go    = cheapest_flight
    transport_ret   = int(cheapest_flight * 0.95)  # pulang biasanya sedikit lebih murah
    transport_total = (transport_go + transport_ret) * n

    # ── HOTEL ────────────────────────────────
    hotel_list = getattr(hotels, hotel_tier, hotels.mid)
    if hotel_list:
        hotel_per_night = hotel_list[0].price_per_night
    else:
        from data.indonesia_db import get_hotel_price_estimate
        hotel_per_night = get_hotel_price_estimate(city)[hotel_tier]

    num_rooms      = max(1, (n + 1) // 2)  # asumsi 2 orang per kamar
    hotel_total    = hotel_per_night * num_rooms * days

    # ── WISATA ────────────────────────────────
    wisata_total   = wisata_cost_per_day * n * days

    # ── MAKAN ────────────────────────────────
    meal_data      = MEAL_COST_ESTIMATE.get(city, MEAL_COST_ESTIMATE["default"])
    meals_daily    = meal_data.get(hotel_tier, meal_data["mid"])
    meals_total    = meals_daily * n * days

    # ── TRANSPORT LOKAL ───────────────────────
    local_daily    = LOCAL_TRANSPORT_ESTIMATE.get(city, LOCAL_TRANSPORT_ESTIMATE["default"])
    local_total    = local_daily * days

    # ── SOUVENIR ──────────────────────────────
    subtotal_sofar = transport_total + hotel_total + wisata_total + meals_total + local_total
    souvenir       = int(subtotal_sofar * SOUVENIR_RATIO)

    # ── EMERGENCY ────────────────────────────
    pre_emergency  = subtotal_sofar + souvenir
    emergency      = int(pre_emergency * EMERGENCY_RATIO)

    grand_total    = pre_emergency + emergency

    # ── ITEMS DETAIL ─────────────────────────
    items = [
        BudgetItem("transport", f"Tiket pesawat PP ({flights.options[0].airline if flights.options else 'Estimasi'})",
                   transport_go + transport_ret, "/orang", n,
                   transport_total, "✈️"),
        BudgetItem("hotel", f"Hotel {hotel_tier.title()} ({hotel_per_night:,} Rp/malam)",
                   hotel_per_night, f"/malam × {num_rooms} kamar", days,
                   hotel_total, "🏨"),
        BudgetItem("wisata", "Tiket wisata (estimasi CSP)",
                   wisata_cost_per_day, "/orang/hari", n * days,
                   wisata_total, "🎟️"),
        BudgetItem("makan", f"Makan & minum ({meals_daily:,} Rp/orang/hari)",
                   meals_daily, "/orang/hari", n * days,
                   meals_total, "🍽️"),
        BudgetItem("lokal", "Transport lokal (ojek/sewa motor)",
                   local_daily, "/hari", days,
                   local_total, "🛵"),
        BudgetItem("souvenir", "Oleh-oleh & belanja (est. 5%)",
                   souvenir, "total", 1,
                   souvenir, "🛍️"),
        BudgetItem("emergency", "Dana cadangan / darurat (10%)",
                   emergency, "total", 1,
                   emergency, "🆘"),
    ]

    surplus = request.budget_total - grand_total

    return BudgetBreakdown(
        transport_go     = transport_go,
        transport_return = transport_ret,
        hotel_per_night  = hotel_per_night,
        hotel_total      = hotel_total,
        wisata_daily     = wisata_cost_per_day,
        wisata_total     = wisata_total,
        meals_daily      = meals_daily,
        meals_total      = meals_total,
        local_transport  = local_total,
        souvenir         = souvenir,
        emergency        = emergency,
        grand_total      = grand_total,
        budget_total     = request.budget_total,
        is_within_budget = grand_total <= request.budget_total,
        surplus_deficit  = surplus,
        items            = items,
        hotel_tier       = hotel_tier,
    )


def suggest_hotel_tier(budget_per_person: int, city: str, num_days: int) -> str:
    """
    Saran tier hotel berdasarkan budget per orang.
    """
    from data.indonesia_db import get_hotel_price_estimate
    prices = get_hotel_price_estimate(city.lower())

    # Hitung berapa budget tersisa setelah transport (estimasi 30% dari budget untuk transport)
    remaining = budget_per_person * 0.4 / num_days

    if remaining >= prices["luxury"] * 0.8:
        return "luxury"
    elif remaining >= prices["mid"] * 0.8:
        return "mid"
    else:
        return "budget"
