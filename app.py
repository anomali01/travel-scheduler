# app.py
"""
Travel Scheduler AI — Full Indonesia Edition
Streamlit Application — Premium UI
"""

import os
import sys
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium
import folium

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from ai.trip_planner    import plan_trip_from_form, TripPlan, DayPlan
from ai.nlp_parser      import parse_trip_request
from data.indonesia_db  import get_all_city_names
from utils.formatter    import fmt_rp, fmt_rp_full, fmt_duration, fmt_date_id, tier_label, tier_color, score_color
from utils.map_utils    import make_itinerary_map

# ──────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TravelAI Indonesia — Smart Trip Planner",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────
# GLOBAL CSS — PREMIUM DARK THEME
# ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');

/* ── ROOT VARIABLES ── */
:root {
    --primary:    #6366f1;
    --primary-d:  #4f46e5;
    --secondary:  #0ea5e9;
    --accent:     #f59e0b;
    --success:    #10b981;
    --danger:     #ef4444;
    --warning:    #f59e0b;
    --bg-dark:    #0f0f1a;
    --bg-card:    #1a1a2e;
    --bg-card2:   #16213e;
    --border:     rgba(255,255,255,0.08);
    --text-1:     #f1f5f9;
    --text-2:     #94a3b8;
    --text-3:     #64748b;
    --radius:     16px;
    --radius-sm:  10px;
    --shadow:     0 8px 32px rgba(0,0,0,0.4);
}

/* ── BASE ── */
html, body, .stApp {
    background: var(--bg-dark) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text-1) !important;
}
.stApp { background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #0d1b2a 100%) !important; }

/* ── HIDE STREAMLIT DEFAULT ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
.block-container { padding: 1.5rem 2rem !important; max-width: 1400px !important; }

/* ── HERO HEADER ── */
.hero-header {
    background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 40%, #0c4a6e 100%);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 24px;
    padding: 2.5rem 3rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(ellipse at 30% 50%, rgba(99,102,241,0.15) 0%, transparent 60%),
                radial-gradient(ellipse at 70% 50%, rgba(14,165,233,0.1) 0%, transparent 60%);
    pointer-events: none;
}
.hero-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 2.6rem;
    font-weight: 800;
    background: linear-gradient(135deg, #e0e7ff, #a5b4fc, #67e8f9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 0.4rem 0;
    line-height: 1.1;
}
.hero-sub {
    color: var(--text-2);
    font-size: 1.05rem;
    margin: 0;
    font-weight: 400;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.78rem;
    color: #a5b4fc;
    margin-bottom: 1rem;
    font-weight: 500;
}

/* ── CARDS ── */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s, transform 0.2s;
}
.card:hover { border-color: rgba(99,102,241,0.3); transform: translateY(-2px); }

.card-title {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-3);
    margin-bottom: 0.6rem;
}

/* ── METRIC CARDS ── */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    margin-bottom: 1.2rem;
}
.metric-card {
    background: linear-gradient(135deg, var(--bg-card2), var(--bg-card));
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 1rem 1.2rem;
    text-align: center;
    transition: all 0.2s;
}
.metric-card:hover { border-color: rgba(99,102,241,0.4); }
.metric-value {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    color: var(--text-1);
    line-height: 1.1;
}
.metric-label {
    font-size: 0.72rem;
    color: var(--text-3);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 4px;
}
.metric-card.primary .metric-value { color: #a5b4fc; }
.metric-card.success .metric-value { color: #6ee7b7; }
.metric-card.warning .metric-value { color: #fcd34d; }
.metric-card.danger  .metric-value { color: #fca5a5; }

/* ── SECTION HEADERS ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 1.8rem 0 1rem 0;
}
.section-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
}
.section-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-1);
}

/* ── FLIGHT CARDS ── */
.flight-card {
    background: linear-gradient(135deg, #1e1b4b, #0f172a);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: var(--radius);
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.8rem;
    transition: all 0.2s;
    position: relative;
    overflow: hidden;
}
.flight-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--primary), var(--secondary));
}
.flight-card:hover { border-color: rgba(99,102,241,0.5); transform: translateX(4px); }
.flight-route {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
}
.flight-time { font-size: 1.3rem; font-weight: 700; color: var(--text-1); }
.flight-arrow { color: var(--text-3); font-size: 1.1rem; }
.flight-airline { font-size: 0.8rem; color: var(--text-2); }
.flight-price { font-size: 1.1rem; font-weight: 700; color: #a5b4fc; }
.flight-badge {
    display: inline-block;
    background: rgba(16,185,129,0.15);
    border: 1px solid rgba(16,185,129,0.3);
    color: #6ee7b7;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 0.7rem;
    font-weight: 600;
}
.flight-badge.transit {
    background: rgba(245,158,11,0.15);
    border-color: rgba(245,158,11,0.3);
    color: #fcd34d;
}

/* ── HOTEL CARDS ── */
.hotel-tier-header {
    font-size: 0.85rem;
    font-weight: 700;
    padding: 0.4rem 1rem;
    border-radius: 8px;
    margin-bottom: 0.8rem;
    display: inline-block;
}
.hotel-card {
    background: var(--bg-card2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    transition: all 0.2s;
}
.hotel-card:hover { border-color: rgba(99,102,241,0.3); }
.hotel-name { font-weight: 600; font-size: 0.95rem; color: var(--text-1); }
.hotel-meta { font-size: 0.78rem; color: var(--text-3); margin-top: 4px; }
.hotel-price { font-weight: 700; font-size: 1rem; margin-top: 6px; }
.hotel-stars { color: #fcd34d; font-size: 0.85rem; }
.amenity-tag {
    display: inline-block;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 0.68rem;
    color: var(--text-3);
    margin: 2px;
}

/* ── ITINERARY ── */
.day-header {
    background: linear-gradient(135deg, var(--primary-d), #1e40af);
    border-radius: var(--radius-sm);
    padding: 0.8rem 1.2rem;
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.day-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 700;
    font-size: 1rem;
    color: white;
}
.day-date { font-size: 0.8rem; color: rgba(255,255,255,0.7); }

.stop-card {
    background: var(--bg-card2);
    border: 1px solid var(--border);
    border-left: 3px solid var(--primary);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    position: relative;
}
.stop-number {
    position: absolute;
    left: -16px; top: 50%;
    transform: translateY(-50%);
    width: 28px; height: 28px;
    background: var(--primary);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700; color: white;
}
.stop-name { font-weight: 600; color: var(--text-1); font-size: 0.9rem; }
.stop-meta { font-size: 0.78rem; color: var(--text-3); margin-top: 3px; }
.travel-arrow {
    text-align: center;
    color: var(--text-3);
    font-size: 0.75rem;
    margin: 3px 0;
    padding-left: 1rem;
}

/* ── BUDGET TABLE ── */
.budget-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.7rem 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.9rem;
}
.budget-row:last-child { border-bottom: none; }
.budget-label { color: var(--text-2); display: flex; align-items: center; gap: 8px; }
.budget-amount { font-weight: 600; color: var(--text-1); }
.budget-total-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 0 0.5rem 0;
    font-size: 1.1rem;
    font-weight: 700;
    border-top: 2px solid var(--border);
    margin-top: 0.5rem;
}
.surplus  { color: #6ee7b7; }
.deficit  { color: #fca5a5; }

/* ── WEATHER ── */
.weather-card {
    background: linear-gradient(135deg, #0c4a6e, #0f172a);
    border: 1px solid rgba(14,165,233,0.2);
    border-radius: var(--radius-sm);
    padding: 0.9rem 1.1rem;
    text-align: center;
    transition: all 0.2s;
}
.weather-icon { font-size: 1.8rem; line-height: 1; }
.weather-temp { font-size: 1rem; font-weight: 700; color: var(--text-1); margin-top: 4px; }
.weather-desc { font-size: 0.72rem; color: var(--text-3); margin-top: 2px; }
.weather-score {
    font-size: 0.7rem;
    font-weight: 700;
    border-radius: 4px;
    padding: 2px 6px;
    margin-top: 4px;
    display: inline-block;
}

/* ── CHAT INPUT ── */
.chat-container {
    background: var(--bg-card);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: var(--radius);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}
.chat-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-2);
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-card) !important;
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
    padding: 4px !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    color: var(--text-3) !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--primary), var(--primary-d)) !important;
    color: white !important;
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 1.2rem !important;
}

/* ── INPUTS ── */
.stTextInput input, .stTextArea textarea, .stSelectbox select,
.stNumberInput input {
    background: var(--bg-card2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-1) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.2) !important;
}

/* ── BUTTONS ── */
.stButton > button {
    background: linear-gradient(135deg, var(--primary), var(--primary-d)) !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.2rem !important;
    transition: all 0.2s !important;
    font-family: 'Inter', sans-serif !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(99,102,241,0.4) !important;
}

/* ── ALERTS ── */
.stSuccess > div { background: rgba(16,185,129,0.1) !important; border-color: rgba(16,185,129,0.3) !important; }
.stWarning > div { background: rgba(245,158,11,0.1) !important; border-color: rgba(245,158,11,0.3) !important; }
.stError   > div { background: rgba(239,68,68,0.1)  !important; border-color: rgba(239,68,68,0.3)  !important; }
.stInfo    > div { background: rgba(14,165,233,0.1)  !important; border-color: rgba(14,165,233,0.3) !important; }

/* ── PROGRESS BAR ── */
.budget-bar-container {
    background: rgba(255,255,255,0.06);
    border-radius: 999px;
    height: 8px;
    overflow: hidden;
    margin: 4px 0;
}
.budget-bar-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.6s ease;
}

/* ── POPULAR DEST CHIPS ── */
.dest-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
}
.dest-chip {
    background: rgba(99,102,241,0.1);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.8rem;
    color: #a5b4fc;
    cursor: pointer;
    transition: all 0.15s;
    font-weight: 500;
}
.dest-chip:hover {
    background: rgba(99,102,241,0.25);
    border-color: rgba(99,102,241,0.5);
}

/* ── API STATUS BADGES ── */
.api-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 0.72rem;
    font-weight: 600;
    margin: 2px;
}
.api-active  { background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); color: #6ee7b7; }
.api-inactive{ background: rgba(100,116,139,0.15); border: 1px solid rgba(100,116,139,0.3); color: #94a3b8; }

/* ── DIVIDER ── */
.fancy-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border), transparent);
    margin: 1.5rem 0;
}

/* ── SPINNER ── */
.stSpinner > div { border-top-color: var(--primary) !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-dark); }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.4); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────────────────────
if "trip_plan"   not in st.session_state: st.session_state.trip_plan   = None
if "active_tab"  not in st.session_state: st.session_state.active_tab  = 0
if "chat_input"  not in st.session_state: st.session_state.chat_input  = ""
if "dest_select" not in st.session_state: st.session_state.dest_select = "Bali"
if "chip_counter"not in st.session_state: st.session_state.chip_counter= 0


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────
def _mc(value: str, label: str, variant: str = ""):
    return f"""
    <div class="metric-card {variant}">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>"""

def _section(icon: str, title: str):
    st.markdown(f"""
    <div class="section-header">
        <div class="section-icon">{icon}</div>
        <div class="section-title">{title}</div>
    </div>""", unsafe_allow_html=True)

def _api_status():
    checks = {
        "Gemini AI"    : bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        "Amadeus"      : bool(os.getenv("AMADEUS_CLIENT_ID")),
        "Google Places": bool(os.getenv("GOOGLE_MAPS_KEY")),
        "Open-Meteo"   : True,   # always free
        "OSM Overpass" : True,   # always free
    }
    badges = ""
    for name, active in checks.items():
        cls = "api-active" if active else "api-inactive"
        dot = "●" if active else "○"
        badges += f'<span class="api-badge {cls}">{dot} {name}</span>'
    return badges


# ──────────────────────────────────────────────────────────────
# RENDER: HERO
# ──────────────────────────────────────────────────────────────
def render_hero():
    st.markdown(f"""
    <div class="hero-header">
        <div class="hero-badge">✈️ AI-Powered Travel Planner • Indonesia Edition</div>
        <h1 class="hero-title">TravelAI Indonesia</h1>
        <p class="hero-sub">
            Rencanakan perjalanan impianmu ke seluruh Indonesia 🇮🇩 — dari Sabang sampai Merauke.<br>
            AI kami menyusun tiket, hotel, cuaca & itinerary harian secara otomatis.
        </p>
        <div style="margin-top: 1rem;">
            {_api_status()}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# RENDER: FORM INPUT
# ──────────────────────────────────────────────────────────────
def render_input_form() -> bool:
    """Render form input. Return True jika user klik Rencanakan."""

    city_names = get_all_city_names()

    # ── Apply NLP parse results SEBELUM widget dirender ──
    if st.session_state.get("_nlp_dest"):
        st.session_state["form_origin"] = st.session_state.pop("_nlp_origin", "Jakarta")
        st.session_state["form_depart"] = st.session_state.pop("_nlp_depart", date.today() + timedelta(weeks=2))
        st.session_state["form_return"] = st.session_state.pop("_nlp_return", date.today() + timedelta(weeks=2, days=4))
        st.session_state["form_people"] = st.session_state.pop("_nlp_people", 2)
        st.session_state["form_budget"] = st.session_state.pop("_nlp_budget", 5_000_000)
        st.session_state["form_prefs"]  = st.session_state.pop("_nlp_prefs",  ["Pantai","Budaya","Alam"])
        st.session_state.pop("_nlp_dest", None)

    # ── Apply chip selection SEBELUM widget dirender ──
    if st.session_state.get("_pending_dest"):
        st.session_state["_dest_override"] = st.session_state.pop("_pending_dest")

    # ── Chat / NLP Input ──
    st.markdown("""
    <div class="chat-label">
        🤖 Ceritakan rencana liburanmu (AI akan memahami otomatis)
    </div>""", unsafe_allow_html=True)

    col_chat, col_parse = st.columns([5, 1])
    with col_chat:
        chat_text = st.text_area(
            label="chat_input_hidden",
            label_visibility="collapsed",
            placeholder='Contoh: "Mau ke Bali dari Jakarta, 4 orang, 5 hari mulai Juni, budget 20 juta total, suka pantai dan budaya"',
            height=80,
            key="nlp_textarea",
        )
    with col_parse:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        parse_btn = st.button("🧠 Parse AI", use_container_width=True, key="btn_parse")

    if parse_btn and chat_text.strip():
        with st.spinner("🤖 AI sedang memahami input..."):
            try:
                req = parse_trip_request(chat_text)
                # Gunakan key _nlp_* (bukan form_* widget key) agar tidak terjadi konflik.
                # Nilai ini akan diapply via index saat rerun berikutnya, SEBELUM widget dibuat.
                st.session_state["_nlp_origin"]  = req.origin
                st.session_state["_nlp_dest"]    = req.destination
                st.session_state["_nlp_depart"]  = req.depart_date
                st.session_state["_nlp_return"]  = req.return_date
                st.session_state["_nlp_people"]  = req.num_people
                st.session_state["_nlp_budget"]  = req.budget_total
                st.session_state["_nlp_prefs"]   = req.preferences
                st.session_state["_pending_dest"]= req.destination
                st.session_state.chip_counter   += 1
                st.info(f"AI memahami: **{req.origin}** → **{req.destination}**, {req.num_days} hari, {req.num_people} org, Rp{req.budget_total:,}")
            except Exception as e:
                st.error(f"Gagal parse: {e}")

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    # ── Form Manual ──
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.markdown("**🛫 Kota Asal**")
        origin = st.selectbox(
            "Asal", city_names,
            index=city_names.index("Jakarta") if "Jakarta" in city_names else 0,
            key="form_origin",
            label_visibility="collapsed"
        )

        st.markdown("**🛬 Kota Tujuan**")
        # Gunakan override jika ada (dari chip selection)
        dest_override = st.session_state.pop("_dest_override", None)
        if dest_override and dest_override in city_names:
            dest_default_idx = city_names.index(dest_override)
        else:
            dest_prev = st.session_state.get("form_dest", "Bali")
            dest_default_idx = city_names.index(dest_prev) if dest_prev in city_names else (
                city_names.index("Bali") if "Bali" in city_names else 0
            )
        destination = st.selectbox(
            "Tujuan", city_names,
            index=dest_default_idx,
            key="form_dest",
            label_visibility="collapsed"
        )

    with col2:
        st.markdown("**📅 Tanggal Berangkat**")
        depart = st.date_input(
            "Berangkat",
            value=st.session_state.get("form_depart", date.today() + timedelta(weeks=2)),
            min_value=date.today(),
            key="form_depart",
            label_visibility="collapsed"
        )
        st.markdown("**📅 Tanggal Pulang**")
        ret_default = st.session_state.get("form_return", depart + timedelta(days=4))
        if ret_default <= depart:
            ret_default = depart + timedelta(days=1)
        ret_date = st.date_input(
            "Pulang",
            value=ret_default,
            min_value=depart + timedelta(days=1),
            key="form_return",
            label_visibility="collapsed"
        )
        num_days = (ret_date - depart).days
        st.markdown(f"<small style='color:#94a3b8'>⏱️ Durasi: **{num_days} hari**</small>", unsafe_allow_html=True)

    with col3:
        st.markdown("**👥 Jumlah Orang**")
        num_people = st.number_input(
            "Orang", min_value=1, max_value=20,
            value=st.session_state.get("form_people", 2),
            key="form_people",
            label_visibility="collapsed"
        )
        st.markdown("**💰 Budget Total (Rp)**")
        budget = st.number_input(
            "Budget", min_value=500_000, max_value=100_000_000,
            value=st.session_state.get("form_budget", 10_000_000),
            step=500_000, format="%d",
            key="form_budget",
            label_visibility="collapsed"
        )
        per_person = budget // max(1, num_people)
        st.markdown(f"<small style='color:#94a3b8'>Per orang: **{fmt_rp(per_person)}**</small>", unsafe_allow_html=True)

    # ── Preferensi & Hotel Tier ──
    col_pref, col_tier, col_hour = st.columns([2, 1, 1])
    with col_pref:
        st.markdown("**🎯 Preferensi Wisata**")
        ALL_PREFS = ["Pantai", "Budaya", "Alam", "Kuliner", "Hiburan", "Religi", "Taman"]
        prefs = st.multiselect(
            "Preferensi",
            ALL_PREFS,
            default=st.session_state.get("form_prefs", ["Pantai", "Budaya", "Alam"]),
            key="form_prefs",
            label_visibility="collapsed"
        )

    with col_tier:
        st.markdown("**🏨 Tier Hotel**")
        hotel_tier = st.selectbox(
            "Tier",
            ["auto", "budget", "mid", "luxury"],
            format_func=lambda x: {"auto":"🤖 Auto","budget":"💚 Budget","mid":"💛 Mid-Range","luxury":"💎 Luxury"}[x],
            key="form_tier",
            label_visibility="collapsed"
        )

    with col_hour:
        st.markdown("**🌅 Jam Mulai Wisata**")
        start_hour = st.selectbox(
            "Jam", list(range(6, 13)),
            format_func=lambda x: f"{x:02d}:00",
            index=2,
            key="form_start_hour",
            label_visibility="collapsed"
        )

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    # ── Submit Button ──
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        submit = st.button(
            "🚀 Rencanakan Perjalanan Sekarang",
            use_container_width=True,
            type="primary",
            key="btn_plan"
        )

    if submit:
        if not prefs:
            st.warning("⚠️ Pilih minimal 1 preferensi wisata.")
            return False
        if ret_date <= depart:
            st.warning("⚠️ Tanggal pulang harus setelah tanggal berangkat.")
            return False
        return True

    return False


# ──────────────────────────────────────────────────────────────
# RENDER: TRANSPORT
# ──────────────────────────────────────────────────────────────
def render_transport(plan: TripPlan):
    _section("✈️", "Transportasi")

    if not plan.flights:
        st.info("Data penerbangan tidak tersedia.")
        return

    f = plan.flights
    src_badge = "🟢 Amadeus API" if f.source == "amadeus" else "🟡 Estimasi Lokal"
    st.markdown(f"<small style='color:#94a3b8'>{src_badge} • {f.note}</small>",
                unsafe_allow_html=True)

    st.markdown("""
    <div class="metric-grid">
    """ + _mc(fmt_rp(f.cheapest_price), "Harga Termurah/Orang", "primary")
        + _mc(fmt_duration(f.fastest_min), "Penerbangan Tercepat", "success")
        + _mc(str(len(f.options)), "Opsi Tersedia", "")
        + """</div>""", unsafe_allow_html=True)

    for opt in f.options[:5]:
        direct_badge = ('<span class="flight-badge">Langsung</span>'
                        if opt.is_direct else
                        f'<span class="flight-badge transit">{opt.stops} Transit</span>')
        st.markdown(f"""
        <div class="flight-card">
            <div class="flight-route">
                <span class="flight-time">{opt.depart_time}</span>
                <span class="flight-arrow">──✈──</span>
                <span class="flight-time">{opt.arrive_time}</span>
                <span style="margin-left:auto">{direct_badge}</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center">
                <span class="flight-airline">✈ {opt.airline} &nbsp;·&nbsp; {opt.flight_code}
                    &nbsp;·&nbsp; {fmt_duration(opt.duration_min)} &nbsp;·&nbsp; {opt.class_type}</span>
                <span class="flight-price">{fmt_rp_full(opt.price)}<small style="color:#64748b">/orang</small></span>
            </div>
            <div style="margin-top: 12px; display: flex; gap: 8px;">
                <a href="{opt.booking_url}" target="_blank" style="background: #0ea5e9; color: white; padding: 4px 10px; border-radius: 6px; text-decoration: none; font-size: 0.75rem; font-weight: bold; transition: all 0.2s;">✈️ Pesan di Traveloka</a>
                <a href="{opt.booking_url_tiket}" target="_blank" style="background: #f59e0b; color: white; padding: 4px 10px; border-radius: 6px; text-decoration: none; font-size: 0.75rem; font-weight: bold; transition: all 0.2s;">🎫 Pesan di Tiket.com</a>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# RENDER: HOTEL
# ──────────────────────────────────────────────────────────────
def render_hotels(plan: TripPlan):
    _section("🏨", "Akomodasi")

    if not plan.hotels:
        st.info("Data hotel tidak tersedia.")
        return

    h = plan.hotels
    src_badge = {"google":"🟢 Google Places","osm":"🟡 OpenStreetMap","local":"⚪ Estimasi Lokal"}.get(h.source, h.source)
    st.markdown(f"<small style='color:#94a3b8'>{src_badge} • {h.note}</small>",
                unsafe_allow_html=True)

    tier_tabs = st.tabs(["💚 Budget", "💛 Mid-Range", "💎 Luxury"])
    tier_data = [("budget", plan.hotels.budget), ("mid", plan.hotels.mid), ("luxury", plan.hotels.luxury)]

    for tab, (tier, hotel_list) in zip(tier_tabs, tier_data):
        with tab:
            if not hotel_list:
                st.info(f"Tidak ada data hotel {tier}.")
                continue
            for hotel in hotel_list:
                stars = "⭐" * int(hotel.rating) + f" {hotel.rating:.1f}"
                amenities_html = "".join(f'<span class="amenity-tag">{a}</span>' for a in hotel.amenities)
                maps_link = f'<a href="{hotel.maps_url}" target="_blank" style="color:#a5b4fc; font-size:0.78rem; text-decoration:none;">📍 Lihat di Maps</a>'
                st.markdown(f"""
                <div class="hotel-card">
                    <div class="hotel-name">{hotel.name}</div>
                    <div class="hotel-stars">{stars} &nbsp; <span style="color:#94a3b8;font-size:0.78rem">{hotel.review_count:,} ulasan</span></div>
                    <div class="hotel-meta">📍 {hotel.address}</div>
                    <div style="margin-top:6px">{amenities_html}</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px">
                        <div class="hotel-price" style="color:{tier_color(tier)}">{fmt_rp_full(hotel.price_per_night)}<small style="color:#64748b">/malam</small></div>
                        {maps_link}
                    </div>
                    <div style="margin-top: 12px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;">
                        <span style="font-size: 0.72rem; color: #64748b; display: block; margin-bottom: 6px;">Pesan Penginapan:</span>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <a href="{hotel.booking_url_traveloka}" target="_blank" style="background: #0ea5e9; color: white; padding: 4px 8px; border-radius: 6px; text-decoration: none; font-size: 0.72rem; font-weight: bold;">🏨 Traveloka</a>
                            <a href="{hotel.booking_url_tiket}" target="_blank" style="background: #f59e0b; color: white; padding: 4px 8px; border-radius: 6px; text-decoration: none; font-size: 0.72rem; font-weight: bold;">🎫 Tiket.com</a>
                            <a href="{hotel.booking_url_agoda}" target="_blank" style="background: #10b981; color: white; padding: 4px 8px; border-radius: 6px; text-decoration: none; font-size: 0.72rem; font-weight: bold;">🌏 Agoda</a>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# RENDER: CUACA
# ──────────────────────────────────────────────────────────────
def render_weather(plan: TripPlan):
    _section("🌤️", "Prakiraan Cuaca")

    if not plan.weather:
        st.info("💡 Data cuaca tidak tersedia (tanggal trip >16 hari ke depan, atau API gagal).")
        return

    w = plan.weather
    st.markdown(f"<div style='color:#94a3b8; font-size:0.85rem; margin-bottom:0.8rem'>🌐 Open-Meteo (gratis) • {w.overall_tip}</div>",
                unsafe_allow_html=True)

    cols = st.columns(min(len(w.daily), 7))
    for i, (col, dw) in enumerate(zip(cols, w.daily)):
        sc = dw.activity_score
        sc_col = score_color(sc)
        with col:
            st.markdown(f"""
            <div class="weather-card">
                <div style="font-size:0.68rem; color:#94a3b8; margin-bottom:4px">{dw.date.strftime('%a %d/%m')}</div>
                <div class="weather-icon">{dw.icon}</div>
                <div class="weather-temp">{dw.temp_max:.0f}° / {dw.temp_min:.0f}°</div>
                <div class="weather-desc">{dw.description}</div>
                <div class="weather-score" style="background:rgba({','.join(str(int(sc_col.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.15); color:{sc_col}; border: 1px solid {sc_col}40">
                    Skor {sc}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# RENDER: ITINERARY
# ──────────────────────────────────────────────────────────────
def render_itinerary(plan: TripPlan):
    _section("📅", "Itinerary Harian")

    if not plan.days:
        st.info("Tidak ada data itinerary.")
        return

    day_tabs = st.tabs([f"Hari {d.day_number}" for d in plan.days])

    for tab, day in zip(day_tabs, plan.days):
        with tab:
            sched = day.schedule
            dw    = day.weather

            # Day header
            weather_info = f"{dw.icon} {dw.description} {dw.temp_max:.0f}°C" if dw else "—"
            status_str   = ""
            if sched and sched.success:
                status_str = f"✅ {len(sched.itinerary)} tempat · Tiket masuk: {fmt_rp(sched.total_cost)}"

            st.markdown(f"""
            <div class="day-header">
                <div>
                    <div class="day-title">Hari {day.day_number} — {fmt_date_id(day.date)}</div>
                    <div class="day-date">{status_str}</div>
                </div>
                <div style="text-align:right; color:rgba(255,255,255,0.7); font-size:0.85rem">{weather_info}</div>
            </div>
            """, unsafe_allow_html=True)

            if dw:
                st.markdown(f"<div style='color:#94a3b8; font-size:0.78rem; margin-bottom:0.8rem'>💡 {dw.tips}</div>",
                            unsafe_allow_html=True)

            if not sched or not sched.success:
                st.warning("⚠️ CSP tidak menemukan jadwal untuk hari ini.")
                continue

            itin = sched.itinerary

            # Stop cards
            st.markdown("<div style='padding-left: 20px'>", unsafe_allow_html=True)
            for i, (_, row) in enumerate(itin.iterrows()):
                cat_colors = {
                    "Pantai":"#0ea5e9","Museum":"#8b5cf6","Taman":"#10b981",
                    "Hiburan":"#f59e0b","Wisata Alam":"#22c55e","Wisata Umum":"#6366f1",
                    "Religi":"#ec4899","Kebun Binatang":"#14b8a6",
                }
                border_color = cat_colors.get(row.get("category",""), "#6366f1")

                # Ambil penjelasan singkat destinasi
                from utils.formatter import get_place_description
                city_name = plan.dest_city.name if plan.dest_city else ""
                desc = get_place_description(row['name'], row.get('category',''), city_name)

                # Badge premium berbayar/gratis
                price = int(row.get('price_idr', 0))
                if price == 0:
                    price_html = '<span style="background: rgba(16, 185, 129, 0.15); color: #10b981; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.72rem;">🟢 Gratis (Bebas Masuk)</span>'
                else:
                    price_html = f'<span style="background: rgba(99, 102, 241, 0.15); color: #818cf8; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.72rem;">🎟️ Berbayar ({fmt_rp_full(price)})</span>'

                # Google Maps Link
                maps_url = f"https://www.google.com/maps/search/?api=1&query={row['lat']},{row['lon']}"
                maps_html = f'<a href="{maps_url}" target="_blank" style="color: #38bdf8; text-decoration: none; font-size: 0.75rem; font-weight: 500;">📍 Buka di Google Maps ↗</a>'

                st.markdown(f"""
                <div class="stop-card" style="border-left-color:{border_color}; margin-left:20px; padding: 1rem 1.2rem;">
                    <div class="stop-number" style="background:{border_color}">{i+1}</div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px; margin-bottom: 4px;">
                        <div class="stop-name" style="font-size: 0.95rem; font-weight: 600; color: white;">{row['name']}</div>
                        <div>{price_html}</div>
                    </div>
                    <div class="stop-meta" style="margin-top: 4px; margin-bottom: 8px; font-size: 0.75rem; color: #94a3b8; display: flex; align-items: center; gap: 8px;">
                        <span style="background: rgba(255,255,255,0.06); color: #cbd5e1; padding: 2px 6px; border-radius: 4px; font-weight: 500;">🏷️ {row.get('category','—')}</span>
                        <span>·</span>
                        {maps_html}
                    </div>
                    <div style="color: #94a3b8; font-size: 0.82rem; line-height: 1.45; border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 8px; margin-top: 8px; font-style: italic;">
                        {desc}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if i < len(itin) - 1:
                    st.markdown('<div class="travel-arrow" style="margin: 8px 0; color: rgba(255,255,255,0.3); font-size: 0.8rem; font-weight: 500; text-align: center; padding-left: 20px;">↓ Rute berikutnya ↓</div>', unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # Map & Charts
            with st.expander("🗺️ Peta Rute Hari Ini", expanded=False):
                m = make_itinerary_map(itin, show_route=True)
                st_folium(m, width=None, height=380, returned_objects=[],
                          key=f"map_day_{day.day_number}")

            with st.expander("📊 Analisis Biaya Masuk Hari Ini", expanded=False):
                if itin["price_idr"].sum() > 0:
                    fig2 = px.pie(
                        itin[itin["price_idr"] > 0], values="price_idr", names="name",
                        title="Distribusi Biaya Tiket Masuk",
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                        hole=0.4,
                    )
                    fig2.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8",
                        margin=dict(t=40,b=0,l=0,r=0),
                    )
                    st.plotly_chart(fig2, use_container_width=True,
                                    key=f"pie_day_{day.day_number}")
                else:
                    st.success("🎉 Semua destinasi hari ini GRATIS! Tidak ada biaya tiket masuk.")


# ──────────────────────────────────────────────────────────────
# RENDER: BUDGET
# ──────────────────────────────────────────────────────────────
def render_budget(plan: TripPlan):
    _section("💰", "Estimasi Budget Lengkap")

    if not plan.budget:
        st.info("Data budget tidak tersedia.")
        return

    b = plan.budget
    pct = min(100, int(b.grand_total / max(1, b.budget_total) * 100))
    bar_color = "#10b981" if b.is_within_budget else "#ef4444"

    # Summary metrics
    surplus_label = f"+{fmt_rp(b.surplus_deficit)}" if b.is_within_budget else f"-{fmt_rp(abs(b.surplus_deficit))}"
    surplus_cls   = "success" if b.is_within_budget else "danger"

    st.markdown("""<div class="metric-grid">"""
        + _mc(fmt_rp(b.grand_total), "Total Estimasi", "primary")
        + _mc(fmt_rp(b.budget_total), "Budget Kamu", "")
        + _mc(surplus_label, "Selisih", surplus_cls)
        + _mc(tier_label(b.hotel_tier), "Tier Hotel", "")
        + """</div>""", unsafe_allow_html=True)

    # Progress bar
    st.markdown(f"""
    <div style="margin-bottom:1rem">
        <div style="display:flex;justify-content:space-between; font-size:0.8rem; color:#94a3b8; margin-bottom:4px">
            <span>Penggunaan Budget</span><span>{pct}%</span>
        </div>
        <div class="budget-bar-container">
            <div class="budget-bar-fill" style="width:{pct}%; background:{'linear-gradient(90deg,#10b981,#059669)' if b.is_within_budget else 'linear-gradient(90deg,#ef4444,#dc2626)'}"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Detail table
    st.markdown('<div class="card">', unsafe_allow_html=True)
    for item in b.items:
        st.markdown(f"""
        <div class="budget-row">
            <span class="budget-label">{item.icon} {item.label}</span>
            <span class="budget-amount">{fmt_rp_full(item.subtotal)}</span>
        </div>
        """, unsafe_allow_html=True)

    surplus_class = "surplus" if b.is_within_budget else "deficit"
    st.markdown(f"""
    <div class="budget-total-row">
        <span>💎 TOTAL ESTIMASI</span>
        <span>{fmt_rp_full(b.grand_total)}</span>
    </div>
    <div style="display:flex;justify-content:space-between; font-size:0.85rem; margin-top:4px">
        <span style="color:#94a3b8">Budget kamu</span>
        <span style="color:#94a3b8">{fmt_rp_full(b.budget_total)}</span>
    </div>
    <div style="display:flex;justify-content:space-between; font-size:1rem; font-weight:700; margin-top:8px">
        <span>{'✅ Sisa' if b.is_within_budget else '⚠️ Kurang'}</span>
        <span class="{surplus_class}">{fmt_rp_full(abs(b.surplus_deficit))}</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Chart
    if b.items:
        chart_data = [{"Kategori": item.icon + " " + item.category.title(), "Biaya": item.subtotal}
                      for item in b.items if item.subtotal > 0]
        if chart_data:
            fig = px.pie(
                chart_data, values="Biaya", names="Kategori",
                hole=0.45,
                color_discrete_sequence=["#6366f1","#0ea5e9","#10b981","#f59e0b","#ec4899","#8b5cf6","#14b8a6"],
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8",
                margin=dict(t=20,b=20,l=0,r=0),
                legend=dict(font=dict(size=11)),
            )
            fig.update_traces(textposition="inside", textinfo="percent+label",
                              textfont_size=11)
            st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────────────────────
# RENDER: TIPS & WARNINGS
# ──────────────────────────────────────────────────────────────
def render_tips(plan: TripPlan):
    if plan.warnings:
        for w in plan.warnings:
            st.warning(w)
    if plan.tips:
        _section("💡", "Tips Perjalanan")
        for tip in plan.tips:
            st.info(tip)


# ──────────────────────────────────────────────────────────────
# RENDER: RESULT
# ──────────────────────────────────────────────────────────────
def render_result(plan: TripPlan):
    if not plan or not plan.success:
        st.error(f"❌ {plan.error_msg if plan else 'Terjadi kesalahan.'}")
        return

    req  = plan.request
    dest = plan.dest_city

    # Summary header
    st.markdown(f"""
    <div class="card" style="background:linear-gradient(135deg,#1e1b4b,#0f172a);border-color:rgba(99,102,241,0.3)">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
            <div>
                <div style="font-size:1.4rem;font-weight:800;color:#e0e7ff;font-family:'Plus Jakarta Sans',sans-serif">
                    {req.origin} ✈️ {req.destination}
                </div>
                <div style="color:#94a3b8;margin-top:4px">
                    {fmt_date_id(req.depart_date)} → {fmt_date_id(req.return_date)} &nbsp;·&nbsp;
                    {req.num_days} hari &nbsp;·&nbsp; {req.num_people} orang
                </div>
            </div>
            <div style="text-align:right">
                <div style="color:#a5b4fc;font-size:0.85rem">Diproses dalam</div>
                <div style="font-size:1.2rem;font-weight:700;color:#e0e7ff">{plan.compute_ms:.0f} ms</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tabs
    tabs = st.tabs(["✈️ Transport", "🏨 Hotel", "🌤️ Cuaca", "📅 Itinerary", "💰 Budget"])

    with tabs[0]: render_transport(plan)
    with tabs[1]: render_hotels(plan)
    with tabs[2]: render_weather(plan)
    with tabs[3]: render_itinerary(plan)
    with tabs[4]: render_budget(plan)

    render_tips(plan)


# ──────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding:1rem 0">
            <div style="font-size:2.5rem">🗺️</div>
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-weight:800;
                        font-size:1.1rem; color:#e0e7ff; margin-top:4px">TravelAI</div>
            <div style="color:#64748b; font-size:0.75rem">Indonesia Edition</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        nav = st.radio("Menu", ["🏠 Trip Planner", "📊 Dataset Explorer", "ℹ️ Tentang"],
                       label_visibility="collapsed")
        st.divider()

        # API Status
        st.markdown("**🔌 Status Integrasi API**")
        apis = {
            "Gemini AI"    : bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "Amadeus"      : bool(os.getenv("AMADEUS_CLIENT_ID")),
            "Google Places": bool(os.getenv("GOOGLE_MAPS_KEY")),
            "Open-Meteo"   : True,
            "OSM Overpass" : True,
        }
        for name, active in apis.items():
            icon = "🟢" if active else "⚪"
            st.markdown(f"<small>{icon} {name}</small>", unsafe_allow_html=True)

        return nav


# ──────────────────────────────────────────────────────────────
# PAGE: DATASET EXPLORER
# ──────────────────────────────────────────────────────────────
def page_dataset():
    st.markdown("""
    <div class="hero-header" style="padding:1.5rem 2rem">
        <h2 style="font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;color:#e0e7ff;margin:0">
            📊 Dataset Explorer
        </h2>
        <p style="color:#94a3b8;margin:4px 0 0 0">Jelajahi data destinasi wisata dari OpenStreetMap</p>
    </div>
    """, unsafe_allow_html=True)

    from data.indonesia_db import CITIES
    city_names = sorted(CITIES.keys())

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_city = st.selectbox("Pilih Kota", city_names,
                                     format_func=lambda x: CITIES[x].name)
    with col2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        fetch_btn = st.button("🔄 Fetch Data OSM", use_container_width=True)

    city = CITIES[selected_city]

    if fetch_btn:
        with st.spinner(f"📡 Mengambil data wisata di {city.name}..."):
            try:
                from data.osm_collector import fetch_wisata
                from data.preprocessing import preprocess
                import os
                raw_path   = f"data/raw/wisata_{city.name.lower()}_raw.csv"
                clean_path = f"data/processed/wisata_{city.name.lower()}_clean.csv"
                os.makedirs("data/raw", exist_ok=True)
                os.makedirs("data/processed", exist_ok=True)
                df_raw = fetch_wisata(kota=city.name, save_path=raw_path)
                if not df_raw.empty:
                    df = preprocess(raw_path, clean_path)
                    st.success(f"✅ {len(df)} destinasi ditemukan di {city.name}")
                    st.session_state[f"dataset_{selected_city}"] = df
                else:
                    st.warning("Tidak ada data dari OSM, menggunakan data lokal.")
            except Exception as e:
                st.error(f"Gagal fetch: {e}")

    # Show existing data
    clean_path = f"data/processed/wisata_{city.name.lower()}_clean.csv"
    if os.path.exists(clean_path):
        df = pd.read_csv(clean_path)
        st.markdown(f"**{len(df)} destinasi wisata di {city.name}**")

        # Filter
        if "category" in df.columns:
            cats = ["Semua"] + sorted(df["category"].unique().tolist())
            sel_cat = st.selectbox("Filter Kategori", cats)
            if sel_cat != "Semua":
                df = df[df["category"] == sel_cat]

        show_cols = [c for c in ["name","category","open_hour","close_hour","duration_min","price_idr","rating"] if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True, height=380)

        # Map
        if "lat" in df.columns and "lon" in df.columns:
            m = folium.Map(location=[city.lat, city.lon], zoom_start=12)
            for _, row in df.iterrows():
                folium.CircleMarker([row["lat"], row["lon"]], radius=5,
                                    color="#6366f1", fill=True, fill_opacity=0.7,
                                    popup=row.get("name","")).add_to(m)
            st_folium(m, width=None, height=400, returned_objects=[],
                      key=f"dataset_map_{selected_city}")
    else:
        st.info(f"Belum ada data untuk {city.name}. Klik **Fetch Data OSM** untuk mengambil.")
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Info Kota</div>
            <b>{city.name}</b>, {city.province}<br>
            Koordinat: {city.lat}, {city.lon}<br>
            Populasi: ~{city.population:,}<br>
            Bandara: {city.airport.name if city.airport else 'Tidak ada'}
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# PAGE: ABOUT
# ──────────────────────────────────────────────────────────────
def page_about():
    st.markdown("""
    <div class="hero-header">
        <div class="hero-badge">ℹ️ Tentang Proyek</div>
        <h1 class="hero-title">AI Travel Scheduler</h1>
        <p class="hero-sub">Full Indonesia Edition — Powered by CSP + Multi-API Integration</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="card">
            <div class="card-title">🧠 Metode AI</div>
            <b>CSP (Constraint Satisfaction Problem)</b><br>
            Google OR-Tools CP-SAT Solver<br><br>
            <b>Formalisasi:</b><br>
            • <code>X</code>: visit[i] ∈ {0,1} per destinasi<br>
            • <code>C1</code>: Σ harga × visit ≤ budget<br>
            • <code>C2</code>: Σ durasi × visit ≤ max_jam × 60<br>
            • <code>C3</code>: jam_buka ≤ jam_mulai<br>
            • <code>C4</code>: selesai sebelum jam tutup<br>
            • <code>OBJ</code>: Maksimalkan Σ rating × visit
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="card">
            <div class="card-title">📦 Teknologi</div>
            • <b>AI Engine</b>: Google OR-Tools CP-SAT<br>
            • <b>NLP</b>: Google Gemini AI (+ rule-based fallback)<br>
            • <b>Data Wisata</b>: OpenStreetMap Overpass API<br>
            • <b>Penerbangan</b>: Amadeus API + estimasi lokal<br>
            • <b>Hotel</b>: Google Places + OSM + local DB<br>
            • <b>Cuaca</b>: Open-Meteo (gratis, no key)<br>
            • <b>Frontend</b>: Streamlit<br>
            • <b>Peta</b>: Folium + Streamlit-Folium<br>
            • <b>Charts</b>: Plotly Express
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
            <div class="card-title">🔌 Integrasi API</div>
            <table style="width:100%;font-size:0.85rem;border-collapse:collapse">
                <tr><td style="padding:6px;border-bottom:1px solid #1e293b"><b>Gemini AI</b></td><td style="color:#94a3b8">NLP Parser · Gratis (quota)</td></tr>
                <tr><td style="padding:6px;border-bottom:1px solid #1e293b"><b>Amadeus</b></td><td style="color:#94a3b8">Flight data · Sandbox gratis</td></tr>
                <tr><td style="padding:6px;border-bottom:1px solid #1e293b"><b>Google Places</b></td><td style="color:#94a3b8">Hotel data · Free tier</td></tr>
                <tr><td style="padding:6px;border-bottom:1px solid #1e293b"><b>Open-Meteo</b></td><td style="color:#94a3b8">Weather · 100% gratis</td></tr>
                <tr><td style="padding:6px"><b>OSM Overpass</b></td><td style="color:#94a3b8">Destinasi wisata · Gratis</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="card">
            <div class="card-title">🗺️ Coverage Indonesia</div>
            • <b>34</b> Provinsi<br>
            • <b>50+</b> Kota dengan data lengkap<br>
            • <b>40+</b> Rute penerbangan terpopuler<br>
            • <b>Semua</b> bandara komersial Indonesia<br><br>
            <b>Kota Wisata Unggulan:</b><br>
            Bali · Yogyakarta · Lombok · Raja Ampat<br>
            Labuan Bajo · Manado · Makassar · Medan
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
def main():
    nav = render_sidebar()

    if nav == "📊 Dataset Explorer":
        page_dataset()
        return
    elif nav == "ℹ️ Tentang":
        page_about()
        return

    # ── TRIP PLANNER (main page) ──
    render_hero()

    submitted = render_input_form()

    if submitted:
        origin     = st.session_state.get("form_origin", "Jakarta")
        dest       = st.session_state.get("form_dest", "Bali")
        depart     = st.session_state.get("form_depart", date.today() + timedelta(weeks=2))
        ret_date   = st.session_state.get("form_return", depart + timedelta(days=4))
        people     = st.session_state.get("form_people", 2)
        budget     = st.session_state.get("form_budget", 10_000_000)
        prefs      = st.session_state.get("form_prefs", ["Pantai","Budaya","Alam"])
        tier       = st.session_state.get("form_tier", "auto")
        start_hour = st.session_state.get("form_start_hour", 8)

        with st.spinner(f"🤖 AI sedang merencanakan trip ke **{dest}**..."):
            plan = plan_trip_from_form(
                origin        = origin,
                destination   = dest,
                depart_date   = depart,
                return_date   = ret_date,
                num_people    = people,
                budget_total  = budget,
                preferences   = prefs,
                start_hour    = start_hour,
                hotel_tier    = tier,
            )
            st.session_state.trip_plan = plan

    if st.session_state.trip_plan:
        st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
        render_result(st.session_state.trip_plan)


if __name__ == "__main__":
    main()
