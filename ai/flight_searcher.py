# ai/flight_searcher.py
"""
Pencari penerbangan — integrasi Amadeus API + estimasi lokal.

Mode 1: Amadeus API (sandbox gratis, perlu API key)
  - Data penerbangan real dari 400+ maskapai
  - Harga aktual (sandbox = data test, bukan live)
  - Register gratis: https://developers.amadeus.com

Mode 2: Local Estimation (fallback, tanpa API key)
  - Berdasarkan database rute indonesia_db.py
  - Estimasi harga berdasarkan data historis
"""

from __future__ import annotations

import os
import requests
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from data.indonesia_db import City, find_route, estimate_travel

# ──────────────────────────────────────────────
# DATA CLASS
# ──────────────────────────────────────────────

@dataclass
class FlightOption:
    airline      : str
    flight_code  : str
    depart_time  : str        # "07:30"
    arrive_time  : str        # "09:15"
    duration_min : int
    price        : int        # Rp
    class_type   : str        # "Economy", "Business"
    is_direct    : bool
    stops        : int        # 0 = langsung
    booking_url  : str = ""   # Deep-link Traveloka
    booking_url_tiket: str = "" # Deep-link Tiket.com


@dataclass
class FlightSearchResult:
    origin_city   : str
    dest_city     : str
    depart_date   : date
    options       : list[FlightOption]
    cheapest_price: int
    fastest_min   : int
    source        : str       # "amadeus" / "local_estimate"
    note          : str


# ──────────────────────────────────────────────
# AMADEUS API
# ──────────────────────────────────────────────

AMADEUS_AUTH_URL   = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


def _get_amadeus_token() -> Optional[str]:
    """Dapatkan Amadeus access token menggunakan client credentials."""
    client_id     = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    try:
        resp = requests.post(AMADEUS_AUTH_URL, data={
            "grant_type"   : "client_credentials",
            "client_id"    : client_id,
            "client_secret": client_secret,
        }, timeout=10)
        resp.raise_for_status()
        return resp.json().get("access_token")
    except Exception as e:
        print(f"⚠️  Amadeus auth failed: {e}")
        return None


def _search_amadeus(origin_iata: str, dest_iata: str,
                    depart_date: date, num_people: int) -> Optional[FlightSearchResult]:
    """Cari penerbangan via Amadeus Flight Offers API."""
    token = _get_amadeus_token()
    if not token:
        return None

    try:
        resp = requests.get(AMADEUS_SEARCH_URL, headers={
            "Authorization": f"Bearer {token}"
        }, params={
            "originLocationCode"     : origin_iata,
            "destinationLocationCode": dest_iata,
            "departureDate"          : depart_date.isoformat(),
            "adults"                 : num_people,
            "max"                    : 5,
            "currencyCode"           : "IDR",
        }, timeout=15)

        if resp.status_code != 200:
            return None

        data = resp.json()
        offers = data.get("data", [])
        if not offers:
            return None

        options = []
        for offer in offers:
            itinerary = offer["itineraries"][0]
            segments  = itinerary["segments"]
            first_seg = segments[0]
            last_seg  = segments[-1]

            # Parse durasi PT1H30M → menit
            dur_str = itinerary.get("duration", "PT2H")
            dur_min = _parse_iso_duration(dur_str)

            price_total = int(float(
                offer["price"]["grandTotal"]
            ))
            price_per   = price_total // max(1, num_people)

            b_url = f"https://www.traveloka.com/id-id/flight/full-search?ap={origin_iata}.{dest_iata}&dt={depart_date.strftime('%d-%m-%Y')}.NA&ps={num_people}.0.0&sc=ECONOMY"
            b_url_tiket = f"https://www.tiket.com/pesawat/search?d={origin_iata}&a={dest_iata}&date={depart_date.isoformat()}&adult={num_people}&child=0&infant=0&class=economy"

            options.append(FlightOption(
                airline      = first_seg["carrierCode"],
                flight_code  = f"{first_seg['carrierCode']}{first_seg['number']}",
                depart_time  = first_seg["departure"]["at"][11:16],
                arrive_time  = last_seg["arrival"]["at"][11:16],
                duration_min = dur_min,
                price        = price_per,
                class_type   = "Economy",
                is_direct    = len(segments) == 1,
                stops        = len(segments) - 1,
                booking_url  = b_url,
                booking_url_tiket = b_url_tiket
            ))

        if not options:
            return None

        return FlightSearchResult(
            origin_city    = origin_iata,
            dest_city      = dest_iata,
            depart_date    = depart_date,
            options        = sorted(options, key=lambda x: x.price),
            cheapest_price = min(o.price for o in options),
            fastest_min    = min(o.duration_min for o in options),
            source         = "amadeus",
            note           = f"Data real dari Amadeus API ({len(options)} opsi ditemukan)",
        )

    except Exception as e:
        print(f"⚠️  Amadeus search failed: {e}")
        return None


def _parse_iso_duration(iso: str) -> int:
    """Konversi ISO 8601 duration (PT1H30M) → menit."""
    import re
    h = re.search(r"(\d+)H", iso)
    m = re.search(r"(\d+)M", iso)
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


# ──────────────────────────────────────────────
# LOCAL ESTIMATION (Fallback)
# ──────────────────────────────────────────────

AIRLINE_SCHEDULES = {
    "Garuda"   : [("06:00","08:00"),("09:00","11:00"),("13:00","15:00"),("16:00","18:00")],
    "Lion Air" : [("05:30","07:30"),("08:00","10:00"),("12:00","14:00"),("17:00","19:00"),("19:00","21:00")],
    "Citilink" : [("06:30","08:30"),("10:00","12:00"),("14:00","16:00"),("18:00","20:00")],
    "Batik Air": [("07:00","09:00"),("11:00","13:00"),("15:00","17:00")],
}


def _search_local(origin: City, dest: City,
                  depart_date: date, num_people: int) -> FlightSearchResult:
    """
    Estimasi penerbangan berdasarkan database lokal.
    Menghasilkan opsi realistis dengan variasi maskapai & jadwal.
    """
    travel = estimate_travel(origin, dest)
    route  = find_route(origin, dest)

    options = []

    airlines_list = route.airlines if route else ["Garuda", "Lion Air", "Citilink"]
    base_dur      = (route.duration_min if route else travel["duration_min"] - 120)
    price_min     = travel["price_min"]
    price_max     = travel["price_max"]

    for i, airline in enumerate(airlines_list[:4]):
        schedules = AIRLINE_SCHEDULES.get(airline, [("08:00","10:00")])
        schedule  = schedules[i % len(schedules)]

        # Variasi harga per maskapai
        if airline in ("Garuda", "Batik Air"):
            price = int(price_min * 1.3)   # premium
        elif airline in ("Citilink",):
            price = int(price_min * 0.9)   # budget
        else:
            price = price_min

        # Variasi harga per tanggal (simulasi dinamis)
        day_factor = 1 + (depart_date.weekday() * 0.05)  # lebih mahal weekend
        price = int(price * day_factor)

        origin_iata = origin.airport.iata if origin.airport else "CGK"
        dest_iata = dest.airport.iata if dest.airport else "DPS"
        b_url = f"https://www.traveloka.com/id-id/flight/full-search?ap={origin_iata}.{dest_iata}&dt={depart_date.strftime('%d-%m-%Y')}.NA&ps={num_people}.0.0&sc=ECONOMY"
        b_url_tiket = f"https://www.tiket.com/pesawat/search?d={origin_iata}&a={dest_iata}&date={depart_date.isoformat()}&adult={num_people}&child=0&infant=0&class=economy"

        options.append(FlightOption(
            airline      = airline,
            flight_code  = f"{airline[:2].upper()}{100 + i * 111}",
            depart_time  = schedule[0],
            arrive_time  = schedule[1],
            duration_min = base_dur + (i * 10),
            price        = price,
            class_type   = "Economy",
            is_direct    = travel.get("has_direct", False),
            stops        = 0 if travel.get("has_direct") else 1,
            booking_url  = b_url,
            booking_url_tiket = b_url_tiket
        ))

    options.sort(key=lambda x: x.price)

    # Tambah opsi Business class
    if options:
        origin_iata = origin.airport.iata if origin.airport else "CGK"
        dest_iata = dest.airport.iata if dest.airport else "DPS"
        b_url = f"https://www.traveloka.com/id-id/flight/full-search?ap={origin_iata}.{dest_iata}&dt={depart_date.strftime('%d-%m-%Y')}.NA&ps={num_people}.0.0&sc=ECONOMY"
        b_url_tiket = f"https://www.tiket.com/pesawat/search?d={origin_iata}&a={dest_iata}&date={depart_date.isoformat()}&adult={num_people}&child=0&infant=0&class=economy"

        business = FlightOption(
            airline      = "Garuda Indonesia",
            flight_code  = f"GA{200}",
            depart_time  = "08:00",
            arrive_time  = "10:00",
            duration_min = base_dur,
            price        = int(price_min * 2.5),
            class_type   = "Business",
            is_direct    = True,
            stops        = 0,
            booking_url  = b_url,
            booking_url_tiket = b_url_tiket
        )
        options.append(business)

    return FlightSearchResult(
        origin_city    = origin.name,
        dest_city      = dest.name,
        depart_date    = depart_date,
        options        = options,
        cheapest_price = min(o.price for o in options) if options else 0,
        fastest_min    = min(o.duration_min for o in options) if options else 0,
        source         = "local_estimate",
        note           = travel["notes"],
    )


# ──────────────────────────────────────────────
# MAIN SEARCH
# ──────────────────────────────────────────────

def search_flights(origin: City, dest: City,
                   depart_date: date,
                   num_people: int = 1) -> FlightSearchResult:
    """
    Cari penerbangan antara dua kota.
    Otomatis gunakan Amadeus API jika tersedia, fallback ke estimasi lokal.
    """
    # Coba Amadeus API
    if origin.airport and dest.airport:
        amadeus_result = _search_amadeus(
            origin.airport.iata,
            dest.airport.iata,
            depart_date,
            num_people
        )
        if amadeus_result:
            return amadeus_result

    # Fallback ke estimasi lokal
    return _search_local(origin, dest, depart_date, num_people)
