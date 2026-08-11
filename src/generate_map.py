"""
Generates an interactive Folium map of flood risk for HSR Layout / Bellandur,
color-coded by risk category, with per-cell popups showing the recommendation.

Input:
    outputs/sponge_city_risk_scored_dataset.csv

Output:
    outputs/sponge_city_risk_map.html
"""

import json

import folium
import pandas as pd
from folium.plugins import Fullscreen

COLOR_MAP = {
    "Low": "#2ecc71",
    "Moderate": "#f1c40f",
    "High": "#e67e22",
    "Critical": "#e74c3c",
}

CENTER_LAT = 12.92
CENTER_LON = 77.655


def build_popup(row: pd.Series) -> str:
    return f"""
    <b>Risk Category:</b> {row['risk_category']}<br>
    <b>Risk Score:</b> {row['risk_score']:.2f}<br>
    <b>Recommendation:</b> {row['recommendation'].replace('_', ' ').title()}<br>
    <hr style='margin:4px 0'>
    <b>Elevation:</b> {row['elevation']:.1f} m<br>
    <b>Impervious surface:</b> {row['impervious']*100:.0f}%<br>
    <b>Distance to water:</b> {row['dist_to_water']:.0f} m
    """


def main():
    df = pd.read_csv("outputs/sponge_city_risk_scored_dataset.csv")

    m = folium.Map(location=[CENTER_LAT, CENTER_LON], zoom_start=14, tiles="CartoDB positron")
    Fullscreen().add_to(m)

    layers = {cat: folium.FeatureGroup(name=f"{cat} Risk") for cat in COLOR_MAP}

    for _, row in df.iterrows():
        geo = json.loads(row[".geo"])
        coords = geo["coordinates"][0]
        latlon_coords = [[c[1], c[0]] for c in coords]

        cat = row["risk_category"]
        color = COLOR_MAP[cat]

        folium.Polygon(
            locations=latlon_coords,
            color=color,
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.55 if cat != "Low" else 0.25,
            popup=folium.Popup(build_popup(row), max_width=250),
        ).add_to(layers[cat])

    for layer in layers.values():
        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; width: 160px;
         background-color: white; border:2px solid grey; z-index:9999; font-size:13px;
         padding: 10px; border-radius: 6px;">
    <b>Flood Risk Legend</b><br>
    <i style="background:#2ecc71;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> Low<br>
    <i style="background:#f1c40f;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> Moderate<br>
    <i style="background:#e67e22;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> High<br>
    <i style="background:#e74c3c;width:12px;height:12px;display:inline-block;margin-right:6px;"></i> Critical
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    title_html = """
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
         background-color: white; border:2px solid grey; z-index:9999; font-size:16px;
         padding: 8px 20px; border-radius: 6px; font-weight:bold;">
    Sponge City Risk Detector — HSR Layout / Bellandur
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    m.save("outputs/sponge_city_risk_map.html")
    print("Saved interactive map to outputs/sponge_city_risk_map.html")


if __name__ == "__main__":
    main()
