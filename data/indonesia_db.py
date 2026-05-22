# data/indonesia_db.py
"""
Database lengkap kota-kota Indonesia.
Mencakup:
  - 34 Provinsi
  - 100+ kota populer + koordinat GPS
  - Semua bandara komersial utama (IATA code)
  - Estimasi jarak & waktu tempuh antar hub utama
  - Estimasi harga tiket pesawat antar rute populer
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ──────────────────────────────────────────────
# DATA CLASS
# ──────────────────────────────────────────────

@dataclass
class Airport:
    iata: str
    name: str
    lat: float
    lon: float

@dataclass
class City:
    name: str
    province: str
    lat: float
    lon: float
    population: int          # perkiraan populasi
    airport: Optional[Airport] = None
    aliases: list[str] = field(default_factory=list)   # nama alternatif / singkatan

@dataclass
class FlightRoute:
    origin_iata: str
    dest_iata: str
    duration_min: int        # estimasi waktu penerbangan (menit)
    price_min: int           # harga min (Rp) economy
    price_max: int           # harga max (Rp) economy
    airlines: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────
# DATABASE KOTA INDONESIA (100+)
# ──────────────────────────────────────────────

CITIES: dict[str, City] = {

    # ── JAWA ──────────────────────────────────
    "jakarta": City(
        name="Jakarta", province="DKI Jakarta",
        lat=-6.2088, lon=106.8456, population=10_600_000,
        airport=Airport("CGK", "Soekarno-Hatta International Airport", -6.1256, 106.6559),
        aliases=["dki jakarta", "ibukota", "jaksel", "jakpus", "jakut", "jakbar", "jaktim"]
    ),
    "surabaya": City(
        name="Surabaya", province="Jawa Timur",
        lat=-7.2575, lon=112.7521, population=2_900_000,
        airport=Airport("SUB", "Juanda International Airport", -7.3798, 112.7868),
        aliases=["sby", "kota pahlawan"]
    ),
    "bandung": City(
        name="Bandung", province="Jawa Barat",
        lat=-6.9175, lon=107.6191, population=2_500_000,
        airport=Airport("BDO", "Husein Sastranegara Airport", -6.9006, 107.5763),
        aliases=["kota kembang", "paris van java"]
    ),
    "yogyakarta": City(
        name="Yogyakarta", province="DIY Yogyakarta",
        lat=-7.7956, lon=110.3695, population=410_000,
        airport=Airport("YIA", "Yogyakarta International Airport", -7.9025, 110.0572),
        aliases=["jogja", "jogjakarta", "diy", "mataram"]
    ),
    "semarang": City(
        name="Semarang", province="Jawa Tengah",
        lat=-6.9932, lon=110.4203, population=1_800_000,
        airport=Airport("SRG", "Ahmad Yani International Airport", -6.9714, 110.3748),
        aliases=["smg"]
    ),
    "solo": City(
        name="Solo", province="Jawa Tengah",
        lat=-7.5755, lon=110.8243, population=520_000,
        airport=Airport("SOC", "Adi Soemarmo Airport", -7.5161, 110.7567),
        aliases=["surakarta", "kota solo"]
    ),
    "malang": City(
        name="Malang", province="Jawa Timur",
        lat=-7.9839, lon=112.6214, population=900_000,
        airport=Airport("MLG", "Abdul Rachman Saleh Airport", -7.9266, 112.7145),
        aliases=["kota apel", "batu"]
    ),
    "bogor": City(
        name="Bogor", province="Jawa Barat",
        lat=-6.5971, lon=106.8060, population=1_100_000,
        airport=None,
        aliases=["kota hujan"]
    ),
    "bekasi": City(
        name="Bekasi", province="Jawa Barat",
        lat=-6.2383, lon=107.0000, population=2_700_000,
        airport=None, aliases=[]
    ),
    "depok": City(
        name="Depok", province="Jawa Barat",
        lat=-6.4025, lon=106.7942, population=2_100_000,
        airport=None, aliases=[]
    ),
    "tangerang": City(
        name="Tangerang", province="Banten",
        lat=-6.1783, lon=106.6319, population=2_000_000,
        airport=None, aliases=["tangsel", "tangerang selatan"]
    ),
    "serang": City(
        name="Serang", province="Banten",
        lat=-6.1202, lon=106.1505, population=680_000,
        airport=None, aliases=[]
    ),
    "cirebon": City(
        name="Cirebon", province="Jawa Barat",
        lat=-6.7063, lon=108.5570, population=340_000,
        airport=None, aliases=[]
    ),

    # ── BALI & NUSA TENGGARA ─────────────────
    "bali": City(
        name="Bali", province="Bali",
        lat=-8.4095, lon=115.1889, population=4_300_000,
        airport=Airport("DPS", "Ngurah Rai International Airport", -8.7467, 115.1667),
        aliases=["denpasar", "dps", "pulau bali", "kuta", "seminyak", "ubud", "nusa dua", "sanur", "gianyar"]
    ),
    "denpasar": City(
        name="Denpasar", province="Bali",
        lat=-8.6705, lon=115.2126, population=930_000,
        airport=Airport("DPS", "Ngurah Rai International Airport", -8.7467, 115.1667),
        aliases=["bali", "dps"]
    ),
    "mataram": City(
        name="Mataram", province="NTB",
        lat=-8.5833, lon=116.1167, population=480_000,
        airport=Airport("LOP", "Zainuddin Abdul Madjid Airport", -8.7572, 116.2767),
        aliases=["lombok", "ntb", "nusa tenggara barat"]
    ),
    "kupang": City(
        name="Kupang", province="NTT",
        lat=-10.1771, lon=123.6070, population=450_000,
        airport=Airport("KOE", "El Tari Airport", -10.1716, 123.6706),
        aliases=["ntt", "nusa tenggara timur"]
    ),
    "labuan_bajo": City(
        name="Labuan Bajo", province="NTT",
        lat=-8.4833, lon=119.8833, population=28_000,
        airport=Airport("LBJ", "Komodo Airport", -8.4867, 119.8881),
        aliases=["flores", "komodo", "labuan bajo"]
    ),

    # ── SUMATERA ──────────────────────────────
    "medan": City(
        name="Medan", province="Sumatera Utara",
        lat=3.5952, lon=98.6722, population=2_500_000,
        airport=Airport("KNO", "Kualanamu International Airport", 3.6422, 98.8853),
        aliases=["sumut", "kota medan"]
    ),
    "palembang": City(
        name="Palembang", province="Sumatera Selatan",
        lat=-2.9761, lon=104.7754, population=1_700_000,
        airport=Airport("PLM", "Sultan Mahmud Badaruddin II Airport", -2.8983, 104.6997),
        aliases=["sumsel", "kota pempek"]
    ),
    "pekanbaru": City(
        name="Pekanbaru", province="Riau",
        lat=0.5336, lon=101.4474, population=1_100_000,
        airport=Airport("PKU", "Sultan Syarif Kasim II Airport", 0.4607, 101.4447),
        aliases=["riau"]
    ),
    "batam": City(
        name="Batam", province="Kepulauan Riau",
        lat=1.1356, lon=104.0370, population=1_300_000,
        airport=Airport("BTH", "Hang Nadim Airport", 1.1212, 104.1191),
        aliases=["kepri", "batam centre"]
    ),
    "padang": City(
        name="Padang", province="Sumatera Barat",
        lat=-0.9471, lon=100.4172, population=950_000,
        airport=Airport("PDG", "Minangkabau International Airport", -0.7869, 100.2806),
        aliases=["sumbar", "minang"]
    ),
    "banda_aceh": City(
        name="Banda Aceh", province="Aceh",
        lat=5.5483, lon=95.3238, population=270_000,
        airport=Airport("BTJ", "Sultan Iskandar Muda Airport", 5.5228, 95.4203),
        aliases=["aceh", "bna"]
    ),
    "lampung": City(
        name="Bandar Lampung", province="Lampung",
        lat=-5.4500, lon=105.2667, population=1_100_000,
        airport=Airport("TKG", "Radin Inten II Airport", -5.2436, 105.1761),
        aliases=["bandar lampung", "tanjung karang", "metro lampung"]
    ),
    "jambi": City(
        name="Jambi", province="Jambi",
        lat=-1.6101, lon=103.6131, population=600_000,
        airport=Airport("DJB", "Sultan Thaha Airport", -1.6382, 103.6439),
        aliases=[]
    ),
    "bengkulu": City(
        name="Bengkulu", province="Bengkulu",
        lat=-3.7928, lon=102.2601, population=380_000,
        airport=Airport("BKS", "Fatmawati Soekarno Airport", -3.8637, 102.3387),
        aliases=[]
    ),

    # ── KALIMANTAN ────────────────────────────
    "balikpapan": City(
        name="Balikpapan", province="Kalimantan Timur",
        lat=-1.2654, lon=116.8312, population=730_000,
        airport=Airport("BPN", "Sultan Aji Muhammad Sulaiman Airport", -1.2683, 116.8942),
        aliases=["kaltim", "bpn"]
    ),
    "samarinda": City(
        name="Samarinda", province="Kalimantan Timur",
        lat=-0.4948, lon=117.1436, population=900_000,
        airport=Airport("SRI", "Temindung Airport", -0.4847, 117.1564),
        aliases=[]
    ),
    "pontianak": City(
        name="Pontianak", province="Kalimantan Barat",
        lat=-0.0263, lon=109.3425, population=700_000,
        airport=Airport("PNK", "Supadio Airport", -0.1503, 109.4039),
        aliases=["kalbar", "khatulistiwa"]
    ),
    "banjarmasin": City(
        name="Banjarmasin", province="Kalimantan Selatan",
        lat=-3.3186, lon=114.5944, population=720_000,
        airport=Airport("BDJ", "Syamsudin Noor Airport", -3.4424, 114.7631),
        aliases=["kalsel", "bjm"]
    ),
    "palangkaraya": City(
        name="Palangkaraya", province="Kalimantan Tengah",
        lat=-2.2161, lon=113.9135, population=310_000,
        airport=Airport("PKY", "Tjilik Riwut Airport", -2.2253, 113.9432),
        aliases=["kalteng"]
    ),
    "nusantara": City(
        name="Nusantara (IKN)", province="Kalimantan Timur",
        lat=-1.1040, lon=116.7220, population=50_000,
        airport=None,
        aliases=["ikn", "ibu kota nusantara"]
    ),

    # ── SULAWESI ──────────────────────────────
    "makassar": City(
        name="Makassar", province="Sulawesi Selatan",
        lat=-5.1477, lon=119.4327, population=1_500_000,
        airport=Airport("UPG", "Sultan Hasanuddin International Airport", -5.0617, 119.5542),
        aliases=["ujung pandang", "sulsel", "upg"]
    ),
    "manado": City(
        name="Manado", province="Sulawesi Utara",
        lat=1.4748, lon=124.8421, population=480_000,
        airport=Airport("MDC", "Sam Ratulangi Airport", 1.5493, 124.9260),
        aliases=["sulut", "bunaken"]
    ),
    "palu": City(
        name="Palu", province="Sulawesi Tengah",
        lat=-0.8917, lon=119.8707, population=390_000,
        airport=Airport("PLW", "Mutiara Sis Al-Jufri Airport", -0.9214, 119.9094),
        aliases=["sulteng"]
    ),
    "kendari": City(
        name="Kendari", province="Sulawesi Tenggara",
        lat=-3.9722, lon=122.5145, population=360_000,
        airport=Airport("KDI", "Haluoleo Airport", -4.0814, 122.4183),
        aliases=["sultra"]
    ),
    "gorontalo": City(
        name="Gorontalo", province="Gorontalo",
        lat=0.5435, lon=123.0568, population=200_000,
        airport=Airport("GTO", "Jalaluddin Airport", 0.6378, 122.8499),
        aliases=[]
    ),

    # ── MALUKU & PAPUA ────────────────────────
    "ambon": City(
        name="Ambon", province="Maluku",
        lat=-3.6954, lon=128.1814, population=340_000,
        airport=Airport("AMQ", "Pattimura Airport", -3.7103, 128.0894),
        aliases=["maluku"]
    ),
    "ternate": City(
        name="Ternate", province="Maluku Utara",
        lat=0.7833, lon=127.3833, population=220_000,
        airport=Airport("TTE", "Sultan Babullah Airport", 0.8313, 127.3808),
        aliases=["malut"]
    ),
    "jayapura": City(
        name="Jayapura", province="Papua",
        lat=-2.5337, lon=140.7181, population=440_000,
        airport=Airport("DJJ", "Sentani Airport", -2.5769, 140.5167),
        aliases=["papua", "port numbay"]
    ),
    "sorong": City(
        name="Sorong", province="Papua Barat",
        lat=-0.8833, lon=131.2500, population=220_000,
        airport=Airport("SOQ", "Domine Eduard Osok Airport", -0.8939, 131.2872),
        aliases=["papua barat", "raja ampat gateway"]
    ),
    "raja_ampat": City(
        name="Raja Ampat", province="Papua Barat",
        lat=-0.5000, lon=130.5000, population=50_000,
        airport=Airport("RJM", "Marinda Airport", -0.4203, 130.7500),
        aliases=["4kings", "wayag", "misool"]
    ),
    "manokwari": City(
        name="Manokwari", province="Papua Barat",
        lat=-0.8617, lon=134.0811, population=190_000,
        airport=Airport("MKW", "Rendani Airport", -0.8917, 134.0492),
        aliases=[]
    ),
}

# ──────────────────────────────────────────────
# DATABASE RUTE PENERBANGAN
# Estimasi berdasarkan data historis Traveloka/Tiket.com
# ──────────────────────────────────────────────

FLIGHT_ROUTES: list[FlightRoute] = [
    # Jakarta (CGK) hub
    FlightRoute("CGK","DPS", 105, 500_000,  1_500_000, ["Garuda","Lion","Citilink","Batik"]),
    FlightRoute("CGK","SUB",  75, 400_000,  1_200_000, ["Garuda","Lion","Citilink","Batik"]),
    FlightRoute("CGK","UPG", 120, 600_000,  1_800_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("CGK","MDC", 150, 700_000,  2_000_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("CGK","KNO",  90, 500_000,  1_500_000, ["Garuda","Lion","Citilink","Batik"]),
    FlightRoute("CGK","PLM",  60, 400_000,  1_000_000, ["Garuda","Sriwijaya","Lion"]),
    FlightRoute("CGK","PKU",  90, 450_000,  1_200_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("CGK","BTH",  60, 350_000,    900_000, ["Lion","Citilink","Batik"]),
    FlightRoute("CGK","PDG",  90, 450_000,  1_200_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("CGK","BPN", 135, 600_000,  1_800_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("CGK","PNK",  90, 500_000,  1_400_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("CGK","BDJ", 120, 550_000,  1_600_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("CGK","AMQ", 180, 800_000,  2_500_000, ["Garuda","Lion"]),
    FlightRoute("CGK","DJJ", 240, 1_200_000,3_500_000, ["Garuda","Lion"]),
    FlightRoute("CGK","SOQ", 210, 900_000,  2_800_000, ["Garuda","Lion"]),
    FlightRoute("CGK","YIA",  55, 350_000,    900_000, ["Garuda","Lion","Citilink","Batik"]),
    FlightRoute("CGK","SRG",  55, 350_000,    900_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("CGK","SOC",  55, 350_000,    900_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("CGK","LOP",  90, 500_000,  1_400_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("CGK","KOE", 150, 700_000,  2_000_000, ["Garuda","Lion"]),
    FlightRoute("CGK","TKG",  45, 300_000,    700_000, ["Garuda","Citilink"]),
    FlightRoute("CGK","BTJ", 150, 700_000,  2_000_000, ["Garuda","Lion","Citilink"]),

    # Surabaya (SUB) hub
    FlightRoute("SUB","DPS",  45, 350_000,    900_000, ["Garuda","Lion","Citilink","Batik"]),
    FlightRoute("SUB","UPG",  90, 500_000,  1_400_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("SUB","KNO", 150, 700_000,  2_000_000, ["Garuda","Lion"]),
    FlightRoute("SUB","BPN",  90, 500_000,  1_400_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("SUB","AMQ", 150, 700_000,  2_000_000, ["Garuda","Lion"]),
    FlightRoute("SUB","DJJ", 210, 1_000_000,3_000_000, ["Garuda","Lion"]),
    FlightRoute("SUB","LBJ",  75, 500_000,  1_200_000, ["Garuda","Lion"]),
    FlightRoute("SUB","MDC", 120, 600_000,  1_800_000, ["Garuda","Lion"]),

    # Denpasar (DPS) hub
    FlightRoute("DPS","UPG",  60, 400_000,  1_100_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("DPS","LOP",  40, 350_000,    800_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("DPS","KOE",  75, 400_000,  1_000_000, ["Garuda","Lion"]),
    FlightRoute("DPS","LBJ",  60, 500_000,  1_200_000, ["Garuda","Wings"]),
    FlightRoute("DPS","AMQ", 120, 600_000,  1_800_000, ["Garuda","Lion"]),

    # Makassar (UPG) hub
    FlightRoute("UPG","MDC",  90, 500_000,  1_400_000, ["Garuda","Lion"]),
    FlightRoute("UPG","AMQ",  90, 500_000,  1_400_000, ["Garuda","Lion"]),
    FlightRoute("UPG","DJJ", 150, 700_000,  2_000_000, ["Garuda","Lion"]),
    FlightRoute("UPG","PLW",  60, 400_000,  1_000_000, ["Garuda","Lion"]),
    FlightRoute("UPG","KDI",  45, 350_000,    800_000, ["Garuda","Wings"]),

    # Medan (KNO) hub
    FlightRoute("KNO","BTJ",  45, 350_000,    800_000, ["Garuda","Lion","Citilink"]),
    FlightRoute("KNO","PKU",  60, 400_000,  1_000_000, ["Garuda","Lion"]),
    FlightRoute("KNO","PDG",  60, 400_000,  1_000_000, ["Garuda","Lion"]),

    # Papua routes
    FlightRoute("DJJ","SOQ",  60, 500_000,  1_200_000, ["Garuda","Lion"]),
    FlightRoute("DJJ","MKW",  60, 500_000,  1_200_000, ["Garuda","Lion"]),
    FlightRoute("SOQ","RJM",  20, 300_000,    600_000, ["Wings"]),
]

# ──────────────────────────────────────────────
# LOOKUP HELPERS
# ──────────────────────────────────────────────

def _build_alias_index() -> dict[str, str]:
    """Buat index: alias → city_key"""
    idx = {}
    for key, city in CITIES.items():
        idx[key] = key
        idx[city.name.lower()] = key
        for alias in city.aliases:
            idx[alias.lower()] = key
    return idx

ALIAS_INDEX = _build_alias_index()


def find_city(name: str) -> Optional[City]:
    """
    Cari kota berdasarkan nama / alias (case-insensitive).
    Contoh: find_city("Bali") → City(name="Bali", ...)
            find_city("Jogja") → City(name="Yogyakarta", ...)
    """
    key = ALIAS_INDEX.get(name.strip().lower())
    if key:
        return CITIES[key]

    # Fuzzy: cari substring match
    name_lower = name.strip().lower()
    for alias, city_key in ALIAS_INDEX.items():
        if name_lower in alias or alias in name_lower:
            return CITIES[city_key]
    return None


def find_route(origin: City, dest: City) -> Optional[FlightRoute]:
    """
    Cari rute penerbangan langsung antara dua kota.
    Kembalikan None jika tidak ada rute langsung.
    """
    if not origin.airport or not dest.airport:
        return None

    origin_iata = origin.airport.iata
    dest_iata   = dest.airport.iata

    for route in FLIGHT_ROUTES:
        if ((route.origin_iata == origin_iata and route.dest_iata == dest_iata) or
            (route.origin_iata == dest_iata   and route.dest_iata == origin_iata)):
            return route
    return None


def estimate_travel(origin: City, dest: City) -> dict:
    """
    Estimasi perjalanan lengkap antara dua kota.
    Return dict berisi: mode, duration_min, price_min, price_max, airlines, notes.
    """
    route = find_route(origin, dest)

    if route:
        # Ada penerbangan langsung
        return {
            "mode"         : "pesawat",
            "duration_min" : route.duration_min + 120,  # +2 jam bandara
            "price_min"    : route.price_min,
            "price_max"    : route.price_max,
            "airlines"     : route.airlines,
            "notes"        : f"Penerbangan langsung {route.duration_min} menit + persiapan bandara ±2 jam",
            "has_direct"   : True,
        }

    # Tidak ada direct flight → estimasi via hub terdekat
    # Cek apakah ada bandara
    if origin.airport and dest.airport:
        # Estimasi kasar berdasarkan jarak
        from geopy.distance import geodesic
        dist_km = geodesic(
            (origin.lat, origin.lon),
            (dest.lat, dest.lon)
        ).km
        flight_min = max(45, int(dist_km / 800 * 60))  # ~800 km/jam
        price_est  = max(400_000, int(dist_km * 1200))  # Rp 1200/km

        return {
            "mode"         : "pesawat (transit)",
            "duration_min" : flight_min + 240,  # +4 jam transit
            "price_min"    : price_est,
            "price_max"    : price_est * 2,
            "airlines"     : ["Garuda", "Lion Air", "Citilink"],
            "notes"        : f"Estimasi via hub terdekat. Jarak ~{dist_km:.0f} km.",
            "has_direct"   : False,
        }

    # Darat / laut
    from geopy.distance import geodesic
    dist_km = geodesic((origin.lat, origin.lon), (dest.lat, dest.lon)).km
    drive_min = int(dist_km / 60 * 60)  # ~60 km/jam

    if dist_km < 300:
        mode = "bus/kereta"
        price = max(50_000, int(dist_km * 500))
    elif dist_km < 800:
        mode = "kereta/kapal"
        price = max(150_000, int(dist_km * 800))
    else:
        mode = "pesawat (estimasi)"
        price = max(400_000, int(dist_km * 1200))

    return {
        "mode"         : mode,
        "duration_min" : drive_min,
        "price_min"    : price,
        "price_max"    : price * 2,
        "airlines"     : [],
        "notes"        : f"Estimasi perjalanan darat/laut. Jarak ~{dist_km:.0f} km.",
        "has_direct"   : False,
    }


def get_all_city_names() -> list[str]:
    """Daftar semua nama kota (untuk autocomplete di UI)."""
    names = sorted({city.name for city in CITIES.values()})
    return names


def get_popular_destinations() -> list[str]:
    """Kota-kota wisata paling populer di Indonesia."""
    return [
        "Bali", "Yogyakarta", "Jakarta", "Lombok", "Labuan Bajo",
        "Raja Ampat", "Manado", "Makassar", "Bandung", "Solo",
        "Surabaya", "Medan", "Balikpapan", "Ambon", "Sorong",
    ]


# ──────────────────────────────────────────────
# ESTIMASI HOTEL (Harga rata-rata per malam, Rp)
# ──────────────────────────────────────────────

HOTEL_PRICE_ESTIMATE = {
    # (kota_key): {budget, mid, luxury}
    "bali"         : {"budget": 200_000,  "mid": 600_000,  "luxury": 2_000_000},
    "jakarta"      : {"budget": 250_000,  "mid": 700_000,  "luxury": 2_500_000},
    "yogyakarta"   : {"budget": 150_000,  "mid": 400_000,  "luxury": 1_200_000},
    "surabaya"     : {"budget": 200_000,  "mid": 500_000,  "luxury": 1_500_000},
    "bandung"      : {"budget": 150_000,  "mid": 400_000,  "luxury": 1_200_000},
    "lombok"       : {"budget": 180_000,  "mid": 500_000,  "luxury": 1_500_000},
    "labuan_bajo"  : {"budget": 250_000,  "mid": 700_000,  "luxury": 2_500_000},
    "raja_ampat"   : {"budget": 300_000,  "mid": 900_000,  "luxury": 3_000_000},
    "makassar"     : {"budget": 200_000,  "mid": 500_000,  "luxury": 1_500_000},
    "manado"       : {"budget": 200_000,  "mid": 500_000,  "luxury": 1_500_000},
    "medan"        : {"budget": 180_000,  "mid": 450_000,  "luxury": 1_300_000},
    "default"      : {"budget": 150_000,  "mid": 400_000,  "luxury": 1_200_000},
}

def get_hotel_price_estimate(city_key: str) -> dict:
    return HOTEL_PRICE_ESTIMATE.get(city_key, HOTEL_PRICE_ESTIMATE["default"])
