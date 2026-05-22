# utils/formatter.py
"""
Helper untuk formatting tampilan di Streamlit.
"""

from __future__ import annotations

def fmt_rp(amount: int) -> str:
    """Format angka ke format Rupiah."""
    if amount >= 1_000_000:
        val = amount / 1_000_000
        return f"Rp {val:.1f} jt" if val % 1 != 0 else f"Rp {int(val)} jt"
    elif amount >= 1_000:
        return f"Rp {amount:,}"
    return f"Rp {amount}"


def fmt_rp_full(amount: int) -> str:
    """Format angka ke format Rupiah lengkap."""
    return f"Rp {amount:,}"


def fmt_duration(minutes: int) -> str:
    """Format menit ke 'X jam Y menit'."""
    h = minutes // 60
    m = minutes % 60
    if h > 0 and m > 0:
        return f"{h} jam {m} mnt"
    elif h > 0:
        return f"{h} jam"
    return f"{m} mnt"


def fmt_date_id(d) -> str:
    """Format tanggal ke Bahasa Indonesia."""
    from datetime import date as _date
    MONTHS = [
        "Jan","Feb","Mar","Apr","Mei","Jun",
        "Jul","Agu","Sep","Okt","Nov","Des"
    ]
    DAYS = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"]
    day_name = DAYS[d.weekday()]
    return f"{day_name}, {d.day} {MONTHS[d.month-1]} {d.year}"


def tier_label(tier: str) -> str:
    return {"budget": "💚 Budget", "mid": "💛 Mid-Range", "luxury": "💎 Luxury"}.get(tier, tier)


def tier_color(tier: str) -> str:
    return {"budget": "#16a34a", "mid": "#d97706", "luxury": "#7c3aed"}.get(tier, "#6b7280")


def score_color(score: int) -> str:
    if score >= 80: return "#16a34a"
    if score >= 60: return "#d97706"
    if score >= 40: return "#ea580c"
    return "#dc2626"


# ──────────────────────────────────────────────
# DICTIONARY DESKRIPSI DESTINASI POPULER
# ──────────────────────────────────────────────
PLACE_DESCRIPTIONS = {
    # Bali
    "tanah lot": "Pura ikonik di atas batu karang besar di tepi laut, terkenal dengan pemandangan matahari terbenam yang spektakuler.",
    "ubud monkey forest": "Cagar alam hutan lindung di Ubud yang rindang, dihuni oleh ratusan kera ekor panjang yang ramah.",
    "pantai kuta": "Pantai berpasir putih legendaris dengan ombak berselancar yang bagus, pusat keramaian dan sunset terindah.",
    "tegallalang rice terrace": "Hamparan sawah terasering hijau berundak-undak khas Ubud yang menyajikan pemandangan alam pedesaan.",
    "pura besakih": "Kompleks pura terbesar, terpenting, dan tersuci bagi umat Hindu di Bali, terletak anggun di lereng Gunung Agung.",
    "seminyak beach": "Pantai modern nan modis yang menawarkan sunset indah dengan deretan beach club dan lounge premium.",
    "museum puri lukisan": "Museum tertua di Ubud yang memamerkan koleksi lukisan dan ukiran kayu tradisional Bali bernilai seni tinggi.",
    "pantai nusa dua": "Kawasan pantai pasir putih eksklusif dengan ombak tenang, sangat cocok untuk berenang dan bersantai.",
    # Yogyakarta
    "candi borobudur": "Candi Buddha terbesar di dunia peninggalan Dinasti Syailendra yang megah, diakui sebagai warisan budaya UNESCO.",
    "candi prambanan": "Kompleks candi Hindu terindah di Asia Tenggara dengan arsitektur menara tinggi yang berkisah tentang Ramayana.",
    "keraton yogyakarta": "Istana resmi Kesultanan Ngayogyakarta Hadiningrat yang melestarikan adat istiadat dan koleksi bersejarah Jawa.",
    "malioboro": "Pusat perbelanjaan ikonik di jantung Yogyakarta, terkenal dengan kerajinan lokal, kuliner, dan suasana hangat.",
    "pantai parangtritis": "Pantai legendaris di selatan Jogja yang terkenal dengan deburan ombak besar, gumuk pasir, dan sunset magis.",
    "taman sari": "Situs istana air bersejarah peninggalan Keraton dengan kolam pemandian indah dan terowongan bawah tanah.",
    # Lombok
    "gili trawangan": "Pulau kecil eksotis bebas polusi kendaraan bermotor, dikelilingi terumbu karang indah dan pantai berpasir putih.",
    "gunung rinjani": "Gunung berapi megah tertinggi kedua di Indonesia dengan pemandangan kaldera Segara Anak yang luar biasa.",
    "pantai selong belanak": "Pantai teluk berpasir sehalus tepung dengan air jernih kehijauan dan ombak tenang yang memikat peselancar.",
    "desa sade": "Desa adat suku Sasak asli Lombok yang kokoh mempertahankan arsitektur rumah tradisional dan seni tenun songket.",
    # Surabaya
    "patung karapan sapi": "Patung perunggu ikonik di pusat kota Surabaya yang menggambarkan budaya adu sapi khas Madura yang penuh energi.",
    "teater kusuma untag": "Gedung pertunjukan seni dan teater di lingkungan kampus UNTAG Surabaya yang aktif menampilkan kreativitas mahasiswa.",
    "monumen kapal selam": "Monumen unik berupa kapal selam KRI Pasopati 410 asli TNI AL, menawarkan wisata edukasi sejarah maritim.",
    "kebun binatang surabaya": "Salah satu kebun binatang tertua dan terlengkap di Asia Tenggara, terletak di pusat kota Surabaya.",
    "house of sampoerna": "Museum industri rokok kretek bersejarah dengan bangunan kolonial bergaya megah dan produksi kretek manual.",
    "jembatan merah": "Jembatan bersejarah di Surabaya yang menjadi saksi bisu pertempuran heroik 10 November 1945.",
    "taman bungkul": "Taman kota terbaik di Surabaya dengan fasilitas lengkap, ruang terbuka hijau rindang, dan pusat kuliner lokal.",
    "masjid nasional al-akbar": "Masjid terbesar kedua di Indonesia dengan kubah biru toska yang megah dan menara pandang setinggi 99 meter.",
}


def get_place_description(name: str, category: str = "", city: str = "") -> str:
    """
    Mengambil deskripsi singkat untuk tempat wisata.
    Mendukung pencarian exact/partial match dari kamus lokal,
    serta fallback deskripsi dinamis berbasis kategori.
    """
    if not name:
        return "Destinasi wisata menarik di Indonesia."
        
    name_lower = name.lower().strip()
    
    # 1. Coba lookup langsung di dictionary
    for k, v in PLACE_DESCRIPTIONS.items():
        if k in name_lower or name_lower in k:
            return v
            
    # 2. Fallback dinamis berbasis kategori jika tidak ada di kamus
    cat = (category or "").strip().lower()
    city_str = f" di {city}" if city else ""
    
    if "pantai" in cat or "pantai" in name_lower:
        return f"{name} adalah destinasi pantai eksotis{city_str} yang menawarkan keindahan panorama pesisir dan suasana santai."
    elif "museum" in cat or "museum" in name_lower:
        return f"{name} merupakan museum bersejarah{city_str} yang menyimpan koleksi edukatif dan warisan budaya yang bernilai tinggi."
    elif "taman" in cat or "taman" in name_lower:
        return f"{name} adalah ruang terbuka hijau/taman asri{city_str} yang sangat cocok untuk bersantai dan menghirup udara segar."
    elif "hiburan" in cat or "rekreasi" in name_lower or "theme" in name_lower:
        return f"{name} merupakan pusat rekreasi keluarga{city_str} dengan berbagai aktivitas menyenangkan untuk melepas penat."
    elif "alam" in cat or "gunung" in name_lower or "air terjun" in name_lower:
        return f"{name} menyajikan pemandangan alam memukau{city_str} dengan suasana sejuk, cocok bagi pecinta petualangan luar ruangan."
    elif "religi" in cat or "masjid" in name_lower or "gereja" in name_lower or "pura" in name_lower or "worship" in cat:
        return f"{name} adalah situs ibadah dan wisata religi{city_str} yang menawarkan arsitektur menawan dan ketenangan spiritual."
    elif "kebun binatang" in cat or "zoo" in cat or "safari" in name_lower:
        return f"{name} adalah destinasi edukasi satwa{city_str} yang melestarikan keanekaragaman fauna dalam lingkungan alam yang asri."
    
    # Default fallback umum
    return f"{name} adalah destinasi wisata populer{city_str} yang menyajikan daya tarik unik dan pengalaman lokal khas bagi pengunjung."

