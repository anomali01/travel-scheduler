# ai/hotel_finder.py
"""
Pencari hotel — integrasi Google Places API + OpenStreetMap fallback.

Mode 1: Google Places API (perlu GOOGLE_MAPS_KEY)
  - Data hotel real dengan rating & review
  - Foto, alamat, jam operasional aktual
  - Register: https://console.cloud.google.com

Mode 2: OpenStreetMap via Overpass API (gratis, no key)
  - Data hotel dari OSM contributors
  - Tidak ada foto/review, tapi gratis

Mode 3: Local Database (ultimate fallback)
  - Estimasi berdasarkan kategori kota
"""

from __future__ import annotations

import os
import requests
from dataclasses import dataclass, field
from typing import Optional

from data.indonesia_db import City, get_hotel_price_estimate

# ──────────────────────────────────────────────
# DATA CLASS
# ──────────────────────────────────────────────

@dataclass
class Hotel:
    name         : str
    tier         : str       # "budget", "mid", "luxury"
    price_per_night: int     # Rp per malam per kamar
    rating       : float     # 0-5
    review_count : int
    address      : str
    lat          : float
    lon          : float
    amenities    : list[str]
    photo_url    : str
    maps_url     : str
    source       : str       # "google", "osm", "local"
    booking_url_traveloka: str = ""
    booking_url_agoda: str = ""
    booking_url_tiket: str = ""


@dataclass
class HotelSearchResult:
    city_name : str
    budget    : list[Hotel]
    mid       : list[Hotel]
    luxury    : list[Hotel]
    source    : str
    note      : str


# ──────────────────────────────────────────────
# GOOGLE PLACES API
# ──────────────────────────────────────────────

GOOGLE_PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
GOOGLE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
GOOGLE_PHOTO_URL  = "https://maps.googleapis.com/maps/api/place/photo"


def _search_google_places(city: City, num_per_tier: int = 3) -> Optional[HotelSearchResult]:
    """Cari hotel via Google Places API."""
    api_key = os.getenv("GOOGLE_MAPS_KEY") or os.getenv("GOOGLE_PLACES_KEY")
    if not api_key:
        return None

    try:
        resp = requests.get(GOOGLE_PLACES_URL, params={
            "location"  : f"{city.lat},{city.lon}",
            "radius"    : 10000,
            "type"      : "lodging",
            "key"       : api_key,
        }, timeout=10)

        if resp.status_code != 200:
            return None

        results = resp.json().get("results", [])
        if not results:
            return None

        hotels_raw = []
        for place in results[:15]:
            rating  = place.get("rating", 3.5)
            reviews = place.get("user_ratings_total", 0)
            name    = place.get("name", "Hotel")
            loc     = place.get("geometry", {}).get("location", {})
            addr    = place.get("vicinity", city.name)

            # Photo URL
            photos = place.get("photos", [])
            if photos and api_key:
                ref = photos[0].get("photo_reference", "")
                photo_url = f"{GOOGLE_PHOTO_URL}?maxwidth=400&photo_reference={ref}&key={api_key}"
            else:
                photo_url = ""

            # Maps URL
            place_id  = place.get("place_id", "")
            maps_url  = f"https://www.google.com/maps/place/?q=place_id:{place_id}"

            # Estimasi harga berdasarkan price_level Google (0-4)
            price_level = place.get("price_level", 2)
            price_estimates = get_hotel_price_estimate(city.name.lower())
            if price_level <= 1:
                price = price_estimates["budget"]
                tier  = "budget"
            elif price_level <= 2:
                price = price_estimates["mid"]
                tier  = "mid"
            else:
                price = price_estimates["luxury"]
                tier  = "luxury"

            b_traveloka = f"https://www.traveloka.com/id-id/hotel/search?q={name.replace(' ', '+')}+{city.name.replace(' ', '+')}"
            b_agoda = f"https://www.agoda.com/search?query={name.replace(' ', '+')}+{city.name.replace(' ', '+')}"
            b_tiket = f"https://www.tiket.com/hotel/search?q={name.replace(' ', '+')}"

            hotels_raw.append(Hotel(
                name           = name,
                tier           = tier,
                price_per_night= price,
                rating         = rating,
                review_count   = reviews,
                address        = addr,
                lat            = loc.get("lat", city.lat),
                lon            = loc.get("lng", city.lon),
                amenities      = _guess_amenities(tier),
                photo_url      = photo_url,
                maps_url       = maps_url,
                source         = "google",
                booking_url_traveloka = b_traveloka,
                booking_url_agoda = b_agoda,
                booking_url_tiket = b_tiket,
            ))

        budget  = sorted([h for h in hotels_raw if h.tier == "budget"],
                         key=lambda x: -x.rating)[:num_per_tier]
        mid     = sorted([h for h in hotels_raw if h.tier == "mid"],
                         key=lambda x: -x.rating)[:num_per_tier]
        luxury  = sorted([h for h in hotels_raw if h.tier == "luxury"],
                         key=lambda x: -x.rating)[:num_per_tier]

        # Jika tier tidak terisi, fill dari list general
        all_sorted = sorted(hotels_raw, key=lambda x: x.price_per_night)
        n = len(all_sorted)
        if not budget and n:
            budget = all_sorted[:min(3, n // 3 + 1)]
            for h in budget: h.tier = "budget"
        if not mid and n > 2:
            mid = all_sorted[n//3:2*n//3][:3]
            for h in mid: h.tier = "mid"
        if not luxury and n:
            luxury = all_sorted[max(0, n - 3):]
            for h in luxury: h.tier = "luxury"

        return HotelSearchResult(
            city_name = city.name,
            budget    = budget,
            mid       = mid,
            luxury    = luxury,
            source    = "google",
            note      = f"Data dari Google Places ({len(results)} hotel ditemukan)",
        )

    except Exception as e:
        print(f"⚠️  Google Places failed: {e}")
        return None


# ──────────────────────────────────────────────
# OSM OVERPASS API (Fallback)
# ──────────────────────────────────────────────

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def _search_osm(city: City, num_per_tier: int = 3) -> Optional[HotelSearchResult]:
    """Cari hotel via OpenStreetMap Overpass API."""
    # Bounding box: ±0.15 derajat dari pusat kota
    delta = 0.15
    bbox  = f"{city.lat - delta},{city.lon - delta},{city.lat + delta},{city.lon + delta}"

    query = f"""
    [out:json][timeout:25];
    (
      node["tourism"="hotel"]({bbox});
      node["tourism"="hostel"]({bbox});
      node["tourism"="motel"]({bbox});
      node["tourism"="guest_house"]({bbox});
    );
    out body;
    """

    try:
        resp = requests.post(OVERPASS_URL, data={"data": query},
                             headers={"User-Agent": "TravelSchedulerAI/2.0"},
                             timeout=30)
        resp.raise_for_status()
        elements = resp.json().get("elements", [])

        if not elements:
            return None

        prices = get_hotel_price_estimate(city.name.lower())
        hotels_all = []

        for i, el in enumerate(elements[:20]):
            tags   = el.get("tags", {})
            name   = tags.get("name", f"Hotel {i+1}")
            stars  = int(tags.get("stars", 0))
            tourism_type = tags.get("tourism", "hotel")

            # Tentukan tier berdasarkan bintang / tipe
            if stars >= 4 or tourism_type in ("resort",):
                tier  = "luxury"
                price = prices["luxury"]
            elif stars >= 3 or tourism_type in ("hotel",):
                tier  = "mid"
                price = prices["mid"]
            else:
                tier  = "budget"
                price = prices["budget"]

            lat = el.get("lat", city.lat)
            lon = el.get("lon", city.lon)

            b_traveloka = f"https://www.traveloka.com/id-id/hotel/search?q={name.replace(' ', '+')}+{city.name.replace(' ', '+')}"
            b_agoda = f"https://www.agoda.com/search?query={name.replace(' ', '+')}+{city.name.replace(' ', '+')}"
            b_tiket = f"https://www.tiket.com/hotel/search?q={name.replace(' ', '+')}"

            hotels_all.append(Hotel(
                name           = name,
                tier           = tier,
                price_per_night= price,
                rating         = 3.5 + (stars * 0.3),
                review_count   = 0,
                address        = tags.get("addr:full", tags.get("addr:street", city.name)),
                lat            = lat,
                lon            = lon,
                amenities      = _guess_amenities(tier),
                photo_url      = "",
                maps_url       = f"https://www.openstreetmap.org/node/{el.get('id', '')}",
                source         = "osm",
                booking_url_traveloka = b_traveloka,
                booking_url_agoda = b_agoda,
                booking_url_tiket = b_tiket,
            ))

        budget = [h for h in hotels_all if h.tier == "budget"][:num_per_tier]
        mid    = [h for h in hotels_all if h.tier == "mid"][:num_per_tier]
        luxury = [h for h in hotels_all if h.tier == "luxury"][:num_per_tier]

        # Pastikan setiap tier terisi
        if not budget:
            budget = _generate_local_hotels(city, "budget", num_per_tier)
        if not mid:
            mid = _generate_local_hotels(city, "mid", num_per_tier)
        if not luxury:
            luxury = _generate_local_hotels(city, "luxury", num_per_tier)

        return HotelSearchResult(
            city_name = city.name,
            budget    = budget,
            mid       = mid,
            luxury    = luxury,
            source    = "osm",
            note      = f"Data dari OpenStreetMap ({len(elements)} hotel ditemukan)",
        )

    except Exception as e:
        print(f"⚠️  OSM hotel fetch failed: {e}")
        return None


# ──────────────────────────────────────────────
# LOCAL DATABASE (Ultimate Fallback)
# ──────────────────────────────────────────────

# Template nama hotel per kota populer
HOTEL_TEMPLATES = {
    "bali": {
        "budget" : ["Kuta Beach Inn", "Seminyak Hostel", "Sanur Budget Stay", "Ubud Guesthouse"],
        "mid"    : ["Bali Garden Beach Resort", "Ayodya Resort", "The Layar Villa", "Alaya Resort Ubud"],
        "luxury" : ["Four Seasons Bali", "The Mulia Nusa Dua", "COMO Uma Ubud", "Alila Seminyak"],
    },
    "yogyakarta": {
        "budget" : ["Matahari Guest House", "Bladok Hotel", "Lotus Guest House"],
        "mid"    : ["Royal Ambarrukmo", "Grand Mercure Yogyakarta", "Cavinton Hotel"],
        "luxury" : ["The Hyatt Regency Yogyakarta", "Tentrem Hotel", "Phoenix Hotel Yogyakarta"],
    },
    "jakarta": {
        "budget" : ["Ibis Styles Jakarta", "Pop! Hotel Kemang", "Fave Hotel"],
        "mid"    : ["Swiss-Belinn Jakarta", "Aryaduta Jakarta", "Mercure Jakarta"],
        "luxury" : ["Hotel Indonesia Kempinski", "The Ritz-Carlton Jakarta", "Mandarin Oriental Jakarta"],
    },
    "surabaya": {
        "budget" : ["Darmo Park Hotel", "Ibis Budget Surabaya", "Pop! Hotel Gubeng"],
        "mid"    : ["Bumi Surabaya City Resort", "Mercure Grand Mirama", "Harper Mangkusumo"],
        "luxury" : ["Sheraton Surabaya", "JW Marriott Surabaya", "Shangri-La Surabaya"],
    },
    "lombok": {
        "budget" : ["Scallywags Resort", "Kuta Indah Hotel", "Rinjani Lodge"],
        "mid"    : ["Katamaran Resort", "Lumbung Lombok", "The Oberoi Beach Resort"],
        "luxury" : ["Qunci Villas", "The Oberoi Beach Resort Lombok", "Amanjiwo"],
    },
}

def _generate_local_hotels(city: City, tier: str, count: int = 3) -> list[Hotel]:
    """Generate hotel list berdasarkan template lokal."""
    city_key  = city.name.lower()
    prices    = get_hotel_price_estimate(city_key)
    templates = HOTEL_TEMPLATES.get(city_key, {})
    names     = templates.get(tier, [f"{tier.title()} Hotel {city.name}", f"Penginapan {city.name}"])

    hotels = []
    for i, name in enumerate(names[:count]):
        base_rating = {"budget": 3.5, "mid": 4.0, "luxury": 4.6}[tier]
        b_traveloka = f"https://www.traveloka.com/id-id/hotel/search?q={name.replace(' ', '+')}+{city.name.replace(' ', '+')}"
        b_agoda = f"https://www.agoda.com/search?query={name.replace(' ', '+')}+{city.name.replace(' ', '+')}"
        b_tiket = f"https://www.tiket.com/hotel/search?q={name.replace(' ', '+')}"
        hotels.append(Hotel(
            name           = name,
            tier           = tier,
            price_per_night= prices[tier],
            rating         = round(base_rating + (i * 0.1), 1),
            review_count   = 100 * (i + 1),
            address        = f"{city.name}, {city.province}",
            lat            = city.lat + (i * 0.01),
            lon            = city.lon + (i * 0.01),
            amenities      = _guess_amenities(tier),
            photo_url      = "",
            maps_url       = f"https://maps.google.com/?q={name}+{city.name}".replace(" ", "+"),
            source         = "local",
            booking_url_traveloka = b_traveloka,
            booking_url_agoda = b_agoda,
            booking_url_tiket = b_tiket,
        ))
    return hotels


def _guess_amenities(tier: str) -> list[str]:
    """Tebak fasilitas berdasarkan tier hotel."""
    base     = ["WiFi", "AC", "Parkir"]
    mid_plus = base + ["Kolam Renang", "Restoran", "Gym"]
    luxury   = mid_plus + ["Spa", "Concierge", "Beach Access", "Butler Service"]
    return {"budget": base, "mid": mid_plus, "luxury": luxury}.get(tier, base)


# ──────────────────────────────────────────────
# MAIN SEARCH
# ──────────────────────────────────────────────

def find_hotels(city: City, num_per_tier: int = 3) -> HotelSearchResult:
    """
    Cari hotel di kota tujuan.
    Urutan prioritas: Google Places → OSM → Local Database
    """
    # 1. Google Places
    result = _search_google_places(city, num_per_tier)
    if result:
        return result

    # 2. OSM
    result = _search_osm(city, num_per_tier)
    if result:
        return result

    # 3. Local fallback
    city_key = city.name.lower()
    prices   = get_hotel_price_estimate(city_key)
    return HotelSearchResult(
        city_name = city.name,
        budget    = _generate_local_hotels(city, "budget", num_per_tier),
        mid       = _generate_local_hotels(city, "mid", num_per_tier),
        luxury    = _generate_local_hotels(city, "luxury", num_per_tier),
        source    = "local",
        note      = "Data estimasi berdasarkan database lokal. Harga aktual dapat berbeda.",
    )
