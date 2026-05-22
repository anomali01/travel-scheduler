# utils/map_utils.py
"""
Utilitas visualisasi peta menggunakan Folium.
Menampilkan lokasi wisata terpilih + rute perjalanan.
"""

import folium
import pandas as pd

# Warna marker berdasarkan urutan kunjungan
MARKER_COLORS = [
    "red", "blue", "green", "purple", "orange",
    "darkred", "lightblue", "darkgreen", "cadetblue", "darkpurple"
]

# Warna marker berdasarkan kategori
CATEGORY_COLORS = {
    "Museum"        : "blue",
    "Taman"         : "green",
    "Pantai"        : "lightblue",
    "Hiburan"       : "orange",
    "Kebun Binatang": "darkgreen",
    "Wisata Alam"   : "darkgreen",
    "Wisata Umum"   : "red",
    "Religi"        : "purple",
}


def make_itinerary_map(df: pd.DataFrame,
                       show_route: bool = True) -> folium.Map:
    """
    Buat peta interaktif dari itinerary hasil CSP.

    Parameter
    ---------
    df         : DataFrame itinerary (output CSP Solver)
    show_route : tampilkan garis rute antar lokasi

    Return
    ------
    folium.Map siap ditampilkan di Streamlit
    """
    if df.empty:
        return folium.Map(location=[-7.265, 112.734], zoom_start=12)

    # Pusatkan peta di rata-rata koordinat
    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    # Tambah marker tiap lokasi
    for idx, (_, row) in enumerate(df.iterrows()):
        cat   = row.get("category", "Wisata Umum")
        color = CATEGORY_COLORS.get(cat, "red")

        popup_html = f"""
        <div style="font-family:Arial; min-width:180px">
            <b style="font-size:14px">📍 {row['name']}</b><br>
            <hr style="margin:4px 0">
            🏷️ <b>Kategori:</b> {cat}<br>
            ⏰ <b>Mulai:</b> {row.get('visit_start','–')} &nbsp;
               <b>Selesai:</b> {row.get('visit_end','–')}<br>
            ⏱️ <b>Durasi:</b> {row['duration_min']} menit<br>
            💰 <b>Tiket:</b> Rp{int(row['price_idr']):,}<br>
            ⭐ <b>Rating:</b> {row['rating']}<br>
            🚗 <b>Travel sebelumnya:</b> {row.get('travel_from_prev', 0)} menit
        </div>
        """

        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{idx + 1}. {row['name']}",
            icon=folium.Icon(
                color=color,
                icon="map-marker",
                prefix="fa"
            )
        ).add_to(m)

        # Nomor urutan kunjungan di atas marker
        folium.Marker(
            location=[row["lat"] + 0.001, row["lon"]],
            icon=folium.DivIcon(
                html=f"""<div style="
                    background:#333; color:white;
                    border-radius:50%; width:22px; height:22px;
                    text-align:center; line-height:22px;
                    font-size:12px; font-weight:bold;
                    box-shadow:0 1px 3px rgba(0,0,0,0.4)">
                    {idx + 1}
                </div>""",
                icon_size=(22, 22),
                icon_anchor=(11, 11)
            )
        ).add_to(m)

    # Garis rute antar lokasi
    if show_route and len(df) > 1:
        coords = list(zip(df["lat"], df["lon"]))
        folium.PolyLine(
            locations=coords,
            color="#2563eb",
            weight=3,
            opacity=0.7,
            dash_array="6 4",
            tooltip="Rute Perjalanan"
        ).add_to(m)

        # Panah arah di tiap segmen rute
        for i in range(len(coords) - 1):
            mid_lat = (coords[i][0] + coords[i+1][0]) / 2
            mid_lon = (coords[i][1] + coords[i+1][1]) / 2
            folium.Marker(
                location=[mid_lat, mid_lon],
                icon=folium.DivIcon(
                    html=f"""<div style="
                        color:#2563eb; font-size:16px;
                        font-weight:bold">➜</div>""",
                    icon_size=(20, 20),
                    icon_anchor=(10, 10)
                )
            ).add_to(m)

    return m


def make_overview_map(df_all: pd.DataFrame) -> folium.Map:
    """
    Buat peta semua tempat wisata dalam dataset (overview).
    Digunakan di tab eksplorasi dataset.
    """
    if df_all.empty:
        return folium.Map(location=[-7.265, 112.734], zoom_start=12)

    center_lat = df_all["lat"].mean()
    center_lon = df_all["lon"].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    for _, row in df_all.iterrows():
        cat   = row.get("category", "Wisata Umum")
        color = CATEGORY_COLORS.get(cat, "gray")

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=6,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=f"{row['name']} ({cat})",
            tooltip=row["name"]
        ).add_to(m)

    return m
