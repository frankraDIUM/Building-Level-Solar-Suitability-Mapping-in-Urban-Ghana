# Accra Solar Rooftop Suitability & Investment Dashboard


import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import FastMarkerCluster
from branca.element import MacroElement
from jinja2 import Template

st.set_page_config(page_title="Accra Solar Dashboard", layout="wide")

# Title
st.markdown("""
<h2 style="font-size: 30px; margin-bottom: 8px;">
    🌞 Accra Solar Rooftop Suitability & Investment Dashboard
</h2>
""", unsafe_allow_html=True)

st.markdown("**Case Study: Central Accra** | Geospatial AI & Economic Modelling")

# Styling
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 20px !important; }
    [data-testid="stMetricLabel"] { font-size: 12px !important; }
    div[data-testid="stHorizontalBlock"] > div { padding: 0 8px !important; }
    .stHeader h2 { font-size: 20px !important; }
</style>
""", unsafe_allow_html=True)

# Optimized Data Loading using cache_resource to prevent MemoryError
@st.cache_resource(show_spinner=True, ttl=600)
def load_data():
    try:
        gdf = gpd.read_parquet("accra_buildings_solar_roi_final_complete.parquet")
    except:
        gdf = gpd.read_file("accra_buildings_solar_roi_final_complete.gpkg")

    if gdf.crs is None or gdf.crs.to_string() != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")

    if 'lat' not in gdf.columns or 'lon' not in gdf.columns:
        gdf_utm = gdf.to_crs("EPSG:32630")
        centroids = gdf_utm.geometry.centroid.to_crs("EPSG:4326")
        gdf = gdf.copy()
        gdf["lat"] = centroids.y
        gdf["lon"] = centroids.x

    # Downcast floats to save memory
    float_cols = gdf.select_dtypes(include=['float64']).columns
    gdf[float_cols] = gdf[float_cols].astype('float32')
    return gdf

@st.cache_resource
def load_hex():
    return gpd.read_file("accra_solar_h3_grid_ready.gpkg")

@st.cache_resource
def load_hotspot():
    return gpd.read_file("accra_solar_h3_with_hotspots.gpkg")

# Load base data
buildings = load_data()
total_buildings_count = len(buildings)

# Filtering logic
def filter_data(_buildings, min_suitability, max_payback, min_npv, min_index):
    return _buildings[
        (_buildings['suitability_score'] >= min_suitability) &
        (_buildings['payback_years'] <= max_payback) &
        (_buildings['npv_ghs'] >= min_npv) &
        (_buildings['solar_index'] >= min_index)
    ].copy()

st.sidebar.header("🔍 Filters")
min_suitability = st.sidebar.slider("Minimum Suitability Score", 0, 100, 40)
max_payback = st.sidebar.slider("Maximum Payback Period (years)", 0, 25, 12)
min_npv = st.sidebar.slider("Minimum NPV (GHS)", -50000, 400000, 0)
min_index = st.sidebar.slider("Minimum Solar Index", 0, 100, 40)

filtered = filter_data(buildings, min_suitability, max_payback, min_npv, min_index)

# ==================== DYNAMIC ROI SIMULATOR ====================
st.sidebar.header("Dynamic ROI Simulator")
tariff = st.sidebar.slider("Electricity Tariff (GHS/kWh)", 1.5, 3.5, 2.15, step=0.05)
discount_rate = st.sidebar.slider("Discount Rate (%)", 5.0, 15.0, 8.5, step=0.5) / 100
self_consumption = st.sidebar.slider("Self-Consumption Rate (%)", 40, 90, 65, step=5) / 100
cost_per_kw = st.sidebar.slider("Installation Cost per kW (GHS)", 5000, 12000, 7000, step=100)

if len(filtered) > 0:
    annual_kwh = filtered['solar_adjusted_kwh_final'].values
    if 'installation_cost_ghs' not in filtered.columns:
        filtered['installation_cost_ghs'] = (filtered['usable_area_m2'] * cost_per_kw).astype('float32')

    installation_cost = filtered['installation_cost_ghs'].values
    annual_savings = annual_kwh * self_consumption * tariff
    annual_om = filtered.get('system_kw', filtered['usable_area_m2'] * 0.2).values * 65
    net_annual = annual_savings - annual_om

    dynamic_payback = np.where(net_annual > 1e-6, installation_cost / net_annual, np.nan)
    dynamic_payback = np.clip(dynamic_payback, 0, 25)

    years = np.arange(1, 26)
    discount_factors = 1 / ((1 + discount_rate) ** years)
    cashflows = np.outer(net_annual, discount_factors)
    dynamic_npv = (cashflows.sum(axis=1) - installation_cost).astype('float32')

    filtered = filtered.copy()
    filtered['dynamic_payback'] = dynamic_payback.astype('float32')
    filtered['dynamic_npv'] = dynamic_npv

    # Priority Score with Alignment Fix
    max_npv = filtered['dynamic_npv'].max()
    min_npv_val = filtered['dynamic_npv'].min()
    npv_scaled = ((filtered['dynamic_npv'] - min_npv_val) / (max_npv - min_npv_val) * 100) if max_npv > min_npv_val else np.zeros(len(filtered))

    hotspot_raw = filtered['hotspot_score'] if 'hotspot_score' in filtered else pd.Series(0, index=filtered.index)
    hotspot_scaled = ((hotspot_raw + 3) / 6) * 100
    risk_penalty = np.where(filtered['dynamic_payback'] > 15, -20, 0)

    filtered['priority_score'] = (0.4 * filtered['solar_index'] + 0.4 * npv_scaled + 0.2 * hotspot_scaled + risk_penalty).astype('float32')

# Header & Metrics
filtered_count = len(filtered)
st.subheader(f"Filtered Buildings: {filtered_count:,} (out of {total_buildings_count:,})")

m_outer1, m_outer2, m_outer3, m_spacer = st.columns([1, 1, 1, 2], gap="small")
with m_outer1:
    st.metric("Avg Payback", f"{filtered['payback_years'].mean():.1f} years")
    st.metric("Dynamic Payback", f"{filtered.get('dynamic_payback', filtered['payback_years']).mean():.1f} years")
with m_outer2:
    st.metric("Avg NPV", f"{filtered['npv_ghs'].mean():,.0f} GHS")
    st.metric("Dynamic NPV", f"{filtered.get('dynamic_npv', filtered['npv_ghs']).mean():,.0f} GHS")
with m_outer3:
    st.metric("Avg Priority Score", f"{filtered.get('priority_score', 50).mean():.1f}")
    st.metric("Total Regional Potential", "~6,000+ GWh/yr")

# Download Data
csv = filtered[['building_id', 'suitability_score', 'solar_index', 'solar_class', 'solar_adjusted_kwh_final', 'payback_years', 'dynamic_payback', 'npv_ghs', 'dynamic_npv', 'priority_score', 'co2_savings_tonnes']].to_csv(index=False)
st.download_button(label="📥 Download Filtered Data as CSV", data=csv, file_name="accra_solar_filtered_buildings.csv", mime="text/csv")

# Tabs
tab1, tab2, tab3 = st.tabs(["Map", " Distributions", " Economic Insights"])

with tab1:
    st.subheader("Solar Suitability Map")
    view_mode = st.radio("View Mode",
                         ["All Buildings", "Solar Potential Density", "Spatial Clusters", "Top Investment Opportunities"],
                         horizontal=True)

    m = folium.Map(location=[5.58, -0.125], zoom_start=12, tiles=None)
    folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri World Imagery', name='Satellite', overlay=False).add_to(m)
    folium.TileLayer(tiles='CartoDB positron', name='Carto Light', overlay=False).add_to(m)

    with st.spinner("Rendering map..."):
        if view_mode == "All Buildings":
            sample_size = min(1500, len(filtered))
            sample = filtered.sample(sample_size, random_state=42).copy()
            marker_cluster = folium.FeatureGroup(name="Cluster View")
            FastMarkerCluster(list(zip(sample["lat"], sample["lon"]))).add_to(marker_cluster)
            marker_cluster.add_to(m)

            # Formatted Legend with Header
            legend_all_html = '''<div style="position: fixed; bottom: 50px; left: 50px; width: auto; min-width: 170px; background-color: white; border:2px solid grey; z-index:9999; font-size:12px; padding: 10px; color: black; box-shadow: 2px 2px 5px rgba(0,0,0,0.2); border-radius: 5px;">
                <b style="display: block; margin-bottom: 8px; border-bottom: 1px solid #ccc;">Solar Class</b>
                <table style="border-spacing: 0 2px;">
                    <tr><td><div style="background:green; width:18px; height:18px; border:0.5px solid black; border-radius:50%;"></div></td><td style="padding-left:8px;">Very High</td></tr>
                    <tr><td><div style="background:orange; width:18px; height:18px; border:0.5px solid black; border-radius:50%;"></div></td><td style="padding-left:8px;">High</td></tr>
                    <tr><td><div style="background:red; width:18px; height:18px; border:0.5px solid black; border-radius:50%;"></div></td><td style="padding-left:8px;">Moderate / Low</td></tr>
                </table></div>'''
            m.get_root().html.add_child(folium.Element(legend_all_html))

        elif view_mode == "Solar Potential Density":
            hex_gdf = load_hex()
            kwh_colors = ['#ffffcc','#ffeb9b','#fdbb84','#fc8d59','#ef6548','#d7301f','#b30000','#7f0000','#4d0000']
            idx_colors = ['#f7fbff','#deebf7','#c6dbef','#9ecae1','#6baed6','#4292c6','#2171b5','#084594','#08306b']
            def get_color(val, colors, max_val):
                if val is None or np.isnan(val) or max_val == 0: return '#808080'
                idx = int((val / max_val) * (len(colors) - 1))
                return colors[max(0, min(idx, len(colors) - 1))]

            max_kwh = hex_gdf['total_solar_kwh'].max()
            max_idx = hex_gdf['avg_solar_index'].max()
            fg_kwh = folium.FeatureGroup(name="Total Solar kWh").add_to(m)
            fg_idx = folium.FeatureGroup(name="Avg Solar Index", show=False).add_to(m)

            folium.GeoJson(hex_gdf, style_function=lambda x: {'fillColor': get_color(x['properties'].get('total_solar_kwh', 0), kwh_colors, max_kwh), 'color': 'black', 'weight': 0.1, 'fillOpacity': 0.8}, tooltip=folium.GeoJsonTooltip(fields=['h3_index', 'total_solar_kwh'])).add_to(fg_kwh)
            folium.GeoJson(hex_gdf, style_function=lambda x: {'fillColor': get_color(x['properties'].get('avg_solar_index', 0), idx_colors, max_idx), 'color': 'black', 'weight': 0.1, 'fillOpacity': 0.8}, tooltip=folium.GeoJsonTooltip(fields=['h3_index', 'avg_solar_index'])).add_to(fg_idx)

            hex_legend_html = f'''<div id="legend-kwh" style="position: fixed; bottom: 50px; left: 50px; width: auto; min-width: 170px; background-color: white; border:2px solid grey; z-index:9999; font-size:12px; padding: 10px; color: black; box-shadow: 2px 2px 5px rgba(0,0,0,0.2); border-radius: 5px; display: block;"><b style="display: block; margin-bottom: 8px; border-bottom: 1px solid #ccc;">Total Solar (kWh)</b><table style="border-spacing: 0 2px;"><tr><td><div style="background:{kwh_colors[-1]}; width:18px; height:18px; border:0.5px solid black;"></div></td><td style="padding-left:8px;">Very High</td></tr><tr><td><div style="background:{kwh_colors[5]}; width:18px; height:18px; border:0.5px solid black;"></div></td><td style="padding-left:8px;">High</td></tr><tr><td><div style="background:{kwh_colors[3]}; width:18px; height:18px; border:0.5px solid black;"></div></td><td style="padding-left:8px;">Medium</td></tr><tr><td><div style="background:{kwh_colors[1]}; width:18px; height:18px; border:0.5px solid black;"></div></td><td style="padding-left:8px;">Low</td></tr></table></div><div id="legend-idx" style="position: fixed; bottom: 50px; left: 50px; width: auto; min-width: 170px; background-color: white; border:2px solid grey; z-index:9999; font-size:12px; padding: 10px; color: black; box-shadow: 2px 2px 5px rgba(0,0,0,0.2); border-radius: 5px; display: none;"><b style="display: block; margin-bottom: 8px; border-bottom: 1px solid #ccc;">Avg Solar Index</b><table style="border-spacing: 0 2px;"><tr><td><div style="background:{idx_colors[-1]}; width:18px; height:18px; border:0.5px solid black;"></div></td><td style="padding-left:8px;">Exceptional</td></tr><tr><td><div style="background:{idx_colors[5]}; width:18px; height:18px; border:0.5px solid black;"></div></td><td style="padding-left:8px;">High</td></tr><tr><td><div style="background:{idx_colors[3]}; width:18px; height:18px; border:0.5px solid black;"></div></td><td style="padding-left:8px;">Medium</td></tr><tr><td><div style="background:{idx_colors[1]}; width:18px; height:18px; border:0.5px solid black;"></div></td><td style="padding-left:8px;">Low</td></tr></table></div>'''
            m.get_root().html.add_child(folium.Element(hex_legend_html))
            js_code = """{% macro script(this, kwargs) %} var kwh_legend = document.getElementById('legend-kwh'); var idx_legend = document.getElementById('legend-idx'); {{this._parent.get_name()}}.on('overlayadd', function(e) { if (e.name === 'Total Solar kWh') { kwh_legend.style.display = 'block'; } if (e.name === 'Avg Solar Index') { idx_legend.style.display = 'block'; } }); {{this._parent.get_name()}}.on('overlayremove', function(e) { if (e.name === 'Total Solar kWh') { kwh_legend.style.display = 'none'; } if (e.name === 'Avg Solar Index') { idx_legend.style.display = 'none'; } }); {% endmacro %}"""
            toggle_macro = MacroElement(); toggle_macro._name = "Legend Toggle Control"; toggle_macro._template = Template(js_code); m.add_child(toggle_macro)

        elif view_mode == "Spatial Clusters":
            hex_hotspot = load_hotspot()
            hotspot_map = {"Hot Spot (99% confidence)": 3, "Hot Spot (95% confidence)": 2, "Hot Spot (90% confidence)": 1, "Not Significant": 0, "Cold Spot (90% confidence)": -1, "Cold Spot (95% confidence)": -2, "Cold Spot (99% confidence)": -3}
            hex_hotspot["hotspot_score"] = hex_hotspot["hotspot_class"].map(hotspot_map).fillna(0)
            folium.Choropleth(geo_data=hex_hotspot, data=hex_hotspot, columns=["h3_index", "hotspot_score"], key_on="feature.properties.h3_index", fill_color="RdYlBu_r", fill_opacity=0.75, line_opacity=0.3, legend_name="Hotspot Classification", name="Hotspots View").add_to(m)

        elif view_mode == "Top Investment Opportunities":
            top_n = max(1, int(0.1 * len(filtered)))
            investment_df = filtered.nlargest(top_n, 'priority_score')
            sample_size = min(1500, len(investment_df))
            sample = investment_df.sample(sample_size, random_state=42).copy()
            top_sample = sample.nlargest(150, 'priority_score')
            top_markers = folium.FeatureGroup(name="Top Investment")

            for _, row in top_sample.iterrows():
                # Cyan used for high satellite visibility
                color = "cyan" if row['dynamic_npv'] > 100000 else "orange" if row['dynamic_npv'] > 50000 else "red"
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=6,
                    color="white",
                    weight=1.5,
                    fill_color=color,
                    fill=True,
                    fill_opacity=1.0,
                    popup=f"ID: {row.get('building_id')}<br>NPV: {row['dynamic_npv']:,.0f} GHS<br>Priority: {row.get('priority_score', 0):.1f}").add_to(top_markers)
            top_markers.add_to(m)

            # Formatted Legend with Header
            legend_inv_html = '''<div style="position: fixed; bottom: 50px; left: 50px; width: auto; min-width: 170px; background-color: white; border:2px solid grey; z-index:9999; font-size:12px; padding: 10px; color: black; box-shadow: 2px 2px 5px rgba(0,0,0,0.2); border-radius: 5px;">
                <b style="display: block; margin-bottom: 8px; border-bottom: 1px solid #ccc;">Investment ROI (NPV)</b>
                <table style="border-spacing: 0 2px;">
                    <tr><td><div style="background:cyan; width:18px; height:18px; border:0.5px solid black; border-radius:50%;"></div></td><td style="padding-left:8px;">High (>100k GHS)</td></tr>
                    <tr><td><div style="background:orange; width:18px; height:18px; border:0.5px solid black; border-radius:50%;"></div></td><td style="padding-left:8px;">Mid (>50k GHS)</td></tr>
                    <tr><td><div style="background:red; width:18px; height:18px; border:0.5px solid black; border-radius:50%;"></div></td><td style="padding-left:8px;">Lower Potential</td></tr>
                </table></div>'''
            m.get_root().html.add_child(folium.Element(legend_inv_html))

        folium.LayerControl().add_to(m)
        st_folium(m, width="100%", height=680, key=f"map_{view_mode}", returned_objects=[])

    if view_mode == "Top Investment Opportunities":
        st.subheader("Investor Summary")
        i_col1, i_col2, i_col3 = st.columns(3)
        i_col1.metric("Total Investment Required", f"{investment_df['installation_cost_ghs'].sum():,.0f} GHS")
        i_col2.metric("Total Projected NPV", f"{investment_df['dynamic_npv'].sum():,.0f} GHS")
        i_col3.metric("Aggregated ROI", f"{(investment_df['dynamic_npv'].sum() / investment_df['installation_cost_ghs'].sum()):.2f}")

        st.subheader("Export Investment Data")
        col_exp = st.columns([1, 4])[0]
        with col_exp:
            geojson_data = investment_df.to_json()
            st.download_button(label="📥 Download GeoJSON", data=geojson_data, file_name="accra_investment_map.geojson", mime="application/json")

with tab2:
    st.subheader("Distributions")
    plot_df = filtered.sample(min(4000, len(filtered)), random_state=42)
    colA, colB = st.columns(2)
    with colA: st.plotly_chart(px.histogram(plot_df, x="solar_index", nbins=30, title="Solar Index"), use_container_width=True)
    with colB: st.plotly_chart(px.histogram(plot_df, x="solar_adjusted_kwh_final", nbins=30, title="Generation (kWh)"), use_container_width=True)

with tab3:
    st.subheader("Economic Insights")
    plot_df = filtered.sample(min(4000, len(filtered)), random_state=42)
    colA, colB = st.columns(2)
    with colA:
        st.plotly_chart(px.scatter(plot_df, x="solar_index", y="payback_years", color="npv_ghs", title="Solar Index vs Payback"), use_container_width=True)
        st.plotly_chart(px.scatter(plot_df, x="priority_score", y="dynamic_payback", color="dynamic_npv", title="Priority Score vs Payback"), use_container_width=True)
    with colB:
        st.plotly_chart(px.box(plot_df, y="payback_years", title="Payback Period Distribution"), use_container_width=True)
    st.subheader("Top 20 Highest Solar Index Buildings")
    st.dataframe(filtered.nlargest(20, "solar_index")[['building_id', 'solar_index', 'solar_class', 'solar_adjusted_kwh_final', 'payback_years']].round(1))

st.caption("Accra Solar Suitability Project | Built with Streamlit & GeoPandas")
