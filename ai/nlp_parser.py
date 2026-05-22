# ai/nlp_parser.py
"""
NLP Parser — mengubah input natural language user menjadi structured TripRequest.

Contoh input : "Saya mau liburan ke Bali bulan depan, 3 orang, budget 5 juta"
Contoh output: TripRequest(dest="Bali", people=3, budget_per_person=1_666_667, ...)

Dua mode:
  1. Gemini AI   — jika GEMINI_API_KEY tersedia (hasil lebih akurat)
  2. Rule-based  — fallback tanpa API key (regex + keyword matching)
"""

from __future__ import annotations

import os
import re
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

# ──────────────────────────────────────────────
# DATA CLASS
# ──────────────────────────────────────────────

@dataclass
class TripRequest:
    """Input terstruktur untuk Trip Planner."""
    origin       : str           # kota asal (default: "Jakarta")
    destination  : str           # kota tujuan
    depart_date  : date          # tanggal berangkat
    return_date  : date          # tanggal pulang
    num_days     : int           # jumlah hari
    num_people   : int           # jumlah orang
    budget_total : int           # total budget (Rp) untuk SEMUA orang
    budget_per_person: int       # budget per orang
    preferences  : list[str]    # preferensi wisata: ["Pantai", "Budaya", ...]
    start_hour   : int           # jam mulai wisata per hari (default: 8)
    raw_input    : str           # input asli user

    @property
    def budget_daily_per_person(self) -> int:
        """Budget harian per orang untuk wisata (tidak termasuk transport & hotel)."""
        return max(50_000, self.budget_per_person // (self.num_days * 3))


# ──────────────────────────────────────────────
# KEYWORD MAPS
# ──────────────────────────────────────────────

PREFERENCE_KEYWORDS = {
    "Pantai"    : ["pantai", "beach", "laut", "snorkeling", "diving", "surfing"],
    "Budaya"    : ["budaya", "kultur", "sejarah", "museum", "candi", "keraton", "heritage"],
    "Alam"      : ["alam", "gunung", "hutan", "waterfall", "air terjun", "trekking", "hiking"],
    "Kuliner"   : ["kuliner", "makan", "food", "wisata kuliner", "restoran"],
    "Hiburan"   : ["hiburan", "theme park", "waterpak", "wahana", "mall"],
    "Religi"    : ["religi", "ziarah", "masjid", "gereja", "pura", "kuil"],
    "Taman"     : ["taman", "park", "kebun"],
}

CITY_KEYWORDS = [
    "bali", "denpasar", "jakarta", "surabaya", "yogyakarta", "jogja",
    "bandung", "semarang", "solo", "malang", "lombok", "mataram",
    "makassar", "manado", "balikpapan", "samarinda", "pontianak",
    "banjarmasin", "palembang", "medan", "padang", "pekanbaru", "batam",
    "ambon", "jayapura", "sorong", "raja ampat", "labuan bajo", "flores",
    "komodo", "ternate", "kupang", "banda aceh",
]


# ──────────────────────────────────────────────
# RULE-BASED PARSER (Fallback)
# ──────────────────────────────────────────────

def _extract_destination(text: str) -> str:
    """Ekstrak nama kota tujuan — prioritaskan pola 'ke/menuju [kota]'."""
    text_lower = text.lower()

    # ── PRIORITAS 1: pola eksplisit arah tujuan ──
    # Stop kata yang menandai akhir nama kota
    _STOP = r"(?=\s+(?:dari|dengan|untuk|pada|tanggal|selama|mulai|bertiga|berdua|berempat|berlima|berenam|sendiri|seorang|\d+\s*(?:orang|hari|malam|juta|ribu)|,|$|\n))"
    dest_patterns = [
        r"(?:ke|menuju|wisata\s+ke|tujuan|liburan\s+ke|pergi\s+ke|jalan\s+ke)\s+([a-z][a-z\s]{1,25}?)" + _STOP,
        r"(?:ke|menuju)\s+([a-z][a-z\s]{1,15}?)" + _STOP,
    ]
    for pat in dest_patterns:
        m = re.search(pat, text_lower)
        if m:
            candidate = m.group(1).strip()
            stop_words = {"sana", "sini", "mana", "luar", "dalam", "kota", "hotel"}
            if candidate not in stop_words and len(candidate) > 2:
                return candidate.title()

    # ── PRIORITAS 2: keyword scan, skip kota asal ──
    origin_candidate = ""
    om = re.search(r"dari\s+([a-z][a-z\s]{2,15}?)(?:\s+ke|\s+menuju|\s*,|$)", text_lower)
    if om:
        origin_candidate = om.group(1).strip()

    for city in sorted(CITY_KEYWORDS, key=len, reverse=True):  # longest first
        if city in text_lower:
            if origin_candidate and city in origin_candidate:
                continue  # ini kota asal, bukan tujuan
            return city.title()

    return "Bali"  # default populer


def _extract_origin(text: str) -> str:
    """Ekstrak kota asal dari teks."""
    patterns = [
        r"dari\s+([A-Za-z\s]{3,15}?)(?:\s+ke|\s+menuju|\s*,|$)",
        r"asal\s+([A-Za-z\s]{3,15}?)(?:\s|,|$)",
        r"berangkat\s+dari\s+([A-Za-z\s]{3,15}?)(?:\s|,|$)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip().title()
    return "Jakarta"


def _extract_people(text: str) -> int:
    """Ekstrak jumlah orang dari teks."""
    # "3 orang", "berdua", "bertiga", "2 orang"
    words = {"seorang":1,"sendiri":1,"berdua":2,"bertiga":3,"berempat":4,"berlima":5,"berenam":6}
    text_lower = text.lower()
    for word, num in words.items():
        if word in text_lower:
            return num

    m = re.search(r"(\d+)\s*(?:orang|pax|person|traveler)", text, re.IGNORECASE)
    if m:
        return max(1, min(int(m.group(1)), 20))
    return 2  # default


def _extract_budget(text: str) -> int:
    """Ekstrak budget total (Rp) dari teks."""
    # "5 juta", "5.000.000", "5jt", "500rb", "500 ribu"
    text_lower = text.lower().replace(".", "").replace(",", "")

    # Pattern juta
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:juta|jt|j\b)", text_lower)
    if m:
        return int(float(m.group(1)) * 1_000_000)

    # Pattern ribu
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:ribu|rb|k\b)", text_lower)
    if m:
        return int(float(m.group(1)) * 1_000)

    # Angka langsung
    m = re.search(r"rp\s*(\d{4,})", text_lower)
    if m:
        return int(m.group(1))

    return 5_000_000  # default 5 juta


def _extract_days(text: str) -> int:
    """Ekstrak durasi perjalanan (hari)."""
    # "3 hari", "seminggu", "3 malam"
    text_lower = text.lower()

    if "seminggu" in text_lower or "1 minggu" in text_lower:
        return 7
    if "2 minggu" in text_lower or "dua minggu" in text_lower:
        return 14

    m = re.search(r"(\d+)\s*(?:hari|malam|night|day)", text_lower)
    if m:
        return max(1, min(int(m.group(1)), 30))
    return 4  # default 4 hari


def _extract_dates(text: str, num_days: int) -> tuple[date, date]:
    """Ekstrak tanggal berangkat & pulang."""
    today = date.today()

    # Cari tanggal eksplisit
    m = re.search(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", text)
    if m:
        day   = int(m.group(1))
        month = int(m.group(2))
        year  = int(m.group(3)) if m.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            depart = date(year, month, day)
            if depart < today:
                depart = depart.replace(year=today.year + 1)
            return depart, depart + timedelta(days=num_days)
        except ValueError:
            pass

    # Bulan keyword
    months = {
        "januari":1,"februari":2,"maret":3,"april":4,"mei":5,"juni":6,
        "juli":7,"agustus":8,"september":9,"oktober":10,"november":11,"desember":12,
        "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
        "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    }
    text_lower = text.lower()
    for month_name, month_num in months.items():
        if month_name in text_lower:
            year = today.year if month_num >= today.month else today.year + 1
            depart = date(year, month_num, 15)  # mid-month default
            return depart, depart + timedelta(days=num_days)

    # Keyword relatif
    if "besok" in text_lower:
        depart = today + timedelta(days=1)
    elif "minggu depan" in text_lower or "pekan depan" in text_lower:
        depart = today + timedelta(weeks=1)
    elif "bulan depan" in text_lower:
        next_month = today.month % 12 + 1
        year = today.year + (1 if today.month == 12 else 0)
        depart = date(year, next_month, 1)
    else:
        depart = today + timedelta(days=7)  # default seminggu lagi

    return depart, depart + timedelta(days=num_days)


def _extract_preferences(text: str) -> list[str]:
    """Ekstrak preferensi wisata dari teks."""
    text_lower = text.lower()
    found = []
    for pref, keywords in PREFERENCE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(pref)
    return found if found else ["Pantai", "Alam", "Budaya"]  # default


def parse_rule_based(text: str) -> TripRequest:
    """
    Parse input natural language menggunakan rule-based approach (regex + keyword).
    Digunakan sebagai fallback jika Gemini API tidak tersedia.
    """
    dest       = _extract_destination(text)
    origin     = _extract_origin(text)
    people     = _extract_people(text)
    budget     = _extract_budget(text)
    num_days   = _extract_days(text)
    depart, ret = _extract_dates(text, num_days)
    prefs      = _extract_preferences(text)

    return TripRequest(
        origin           = origin,
        destination      = dest,
        depart_date      = depart,
        return_date      = ret,
        num_days         = num_days,
        num_people       = people,
        budget_total     = budget,
        budget_per_person= budget // max(1, people),
        preferences      = prefs,
        start_hour       = 8,
        raw_input        = text,
    )


# ──────────────────────────────────────────────
# GEMINI AI PARSER (jika API key tersedia)
# ──────────────────────────────────────────────

def parse_with_gemini(text: str) -> Optional[TripRequest]:
    """
    Parse input natural language menggunakan Gemini AI.
    Mendukung google-genai (baru) dan google-generativeai (lama).
    Return None jika API key tidak tersedia atau gagal.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        # Coba new SDK (google-genai) dulu
        try:
            from google import genai as new_genai
            client = new_genai.Client(api_key=api_key)
            _use_new_sdk = True
        except ImportError:
            # Fallback ke old SDK (google-generativeai)
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            _use_new_sdk = False

        today_str = date.today().isoformat()
        prompt = f"""Kamu adalah parser trip planning untuk wisata Indonesia.
Hari ini: {today_str}
Ekstrak informasi dari teks berikut dan kembalikan HANYA JSON valid tanpa markdown.

Teks: "{text}"

Format JSON:
{{
  "origin": "nama kota asal (default: Jakarta)",
  "destination": "nama kota tujuan",
  "depart_date": "YYYY-MM-DD",
  "return_date": "YYYY-MM-DD",
  "num_days": angka_hari_integer,
  "num_people": angka_orang_integer,
  "budget_total": angka_rupiah_integer,
  "preferences": ["Pantai","Budaya","Alam","Kuliner","Hiburan","Religi","Taman"],
  "start_hour": angka_jam_mulai_integer_default_8
}}

Aturan:
- budget_total = budget TOTAL semua orang (Rp)
- Jika tidak ada info tanggal, gunakan 7 hari dari sekarang
- preferences hanya dari list: Pantai, Budaya, Alam, Kuliner, Hiburan, Religi, Taman
- Jika tidak ada preferensi, gunakan ["Pantai","Budaya","Alam"]
"""
        if _use_new_sdk:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            raw = response.text.strip()
        else:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            raw = response.text.strip()

        # Bersihkan markdown jika ada
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
        data = json.loads(raw)

        depart = date.fromisoformat(data["depart_date"])
        ret    = date.fromisoformat(data["return_date"])
        people = max(1, int(data.get("num_people", 2)))
        budget = int(data.get("budget_total", 5_000_000))

        return TripRequest(
            origin           = data.get("origin", "Jakarta"),
            destination      = data.get("destination", "Bali"),
            depart_date      = depart,
            return_date      = ret,
            num_days         = int(data.get("num_days", (ret - depart).days)),
            num_people       = people,
            budget_total     = budget,
            budget_per_person= budget // people,
            preferences      = data.get("preferences", ["Pantai","Budaya","Alam"]),
            start_hour       = int(data.get("start_hour", 8)),
            raw_input        = text,
        )

    except Exception as e:
        print(f"⚠️  Gemini parse failed: {e}")
        return None


# ──────────────────────────────────────────────
# MAIN PARSER (otomatis pilih mode)
# ──────────────────────────────────────────────

def parse_trip_request(text: str) -> TripRequest:
    """
    Parse input user menjadi TripRequest terstruktur.
    Otomatis gunakan Gemini AI jika tersedia, fallback ke rule-based.
    """
    if not text or not text.strip():
        raise ValueError("Input tidak boleh kosong.")

    # Coba Gemini dulu
    result = parse_with_gemini(text)
    if result:
        result.raw_input = text
        return result

    # Fallback rule-based
    return parse_rule_based(text)
