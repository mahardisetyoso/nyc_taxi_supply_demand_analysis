import streamlit as st
import psycopg2
import pandas as pd
import pydeck as pdk
import os
import json
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

st.set_page_config(
    page_title="GeoOps · NYC Taxi Supply-Demand",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    section[data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #1e2433; }
    .kpi-card { background: #111827; border: 1px solid #1e2433; border-radius: 8px; padding: 16px 18px; text-align: left; }
    .kpi-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
    .kpi-value { font-size: 24px; font-weight: 600; color: #f1f5f9; line-height: 1.2; }
    .kpi-delta { font-size: 11px; margin-top: 4px; }
    .kpi-delta.up { color: #34d399; }
    .kpi-delta.down { color: #f87171; }
    .kpi-delta.neutral { color: #64748b; }
    .finding-item { background: #111827; border: 1px solid #1e2433; border-left: 3px solid; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; }
    .finding-item.high { border-left-color: #ef4444; }
    .finding-item.med { border-left-color: #f59e0b; }
    .finding-item.low { border-left-color: #3b82f6; }
    .finding-title { font-size: 13px; color: #e2e8f0; font-weight: 500; }
    .finding-desc { font-size: 11px; color: #94a3b8; margin-top: 3px; }
    .finding-badge { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 3px; margin-top: 5px; }
    .finding-badge.high { background: #3f1010; color: #f87171; }
    .finding-badge.med { background: #3f2a10; color: #fbbf24; }
    .finding-badge.low { background: #1e3a5f; color: #60a5fa; }
    .section-title { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid #1e2433; }
    .status-row { display: flex; align-items: center; gap: 10px; padding: 8px 10px; background: #111827; border: 1px solid #1e2433; border-radius: 6px; margin-bottom: 6px; }
    .status-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
    .status-name { font-size: 13px; color: #cbd5e1; flex: 1; }
    .status-count { font-size: 12px; color: #64748b; }
    .status-bar-bg { height: 3px; background: #1e2433; border-radius: 2px; margin-top: 4px; width: 100%; }
    .status-bar-fill { height: 3px; border-radius: 2px; }
    #MainMenu { visibility: hidden; }
    header[data-testid="stHeader"] { background: #0f1117; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_zones():
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"])
    df = pd.read_sql("""
        SELECT zone_name, borough, h3_cell, zone_status,
            total_demand_trips, total_supply_trips,
            supply_demand_ratio, unmet_demand_rate, oversupply_ratio,
            estimated_revenue_loss_usd, estimated_unmet_trips,
            road_segment_count,
            ST_AsGeoJSON(geom) AS geom_json
        FROM revenue_loss_by_zone WHERE geom IS NOT NULL
        ORDER BY estimated_revenue_loss_usd DESC
    """, conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_transit():
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"])
    df = pd.read_sql("""
        SELECT hub.name AS hub_name, r.zone_name, r.borough,
            ROUND(r.estimated_revenue_loss_usd::numeric, 0) AS revenue_loss,
            ROUND(ST_Distance(r.geom::geography,
                ST_SetSRID(ST_MakePoint(hub.lng, hub.lat), 4326)::geography
            )::numeric, 0) AS distance_meters
        FROM revenue_loss_by_zone r
        CROSS JOIN (VALUES
            ('Penn Station',-73.9934,40.7506),('Grand Central',-73.9772,40.7527),
            ('Port Authority',-73.9903,40.7571),('Union Square',-73.9897,40.7359),
            ('JFK AirTrain Hub',-73.7789,40.6413)
        ) AS hub(name, lng, lat)
        WHERE r.zone_status = 'UNDERSUPPLIED'
          AND ST_Within(ST_Centroid(r.geom),
              ST_Buffer(ST_SetSRID(ST_MakePoint(hub.lng, hub.lat), 4326)::geography, 800)::geometry)
        ORDER BY revenue_loss DESC
    """, conn)
    conn.close()
    return df

with st.spinner("Loading zone data..."):
    df = load_zones()
    


undersupplied = df[df['zone_status'] == 'UNDERSUPPLIED']
balanced = df[df['zone_status'] == 'BALANCED']
oversupplied = df[df['zone_status'] == 'OVERSUPPLIED']
total_loss = undersupplied['estimated_revenue_loss_usd'].sum()

# Header
st.markdown("""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
    <div style="width:32px; height:32px; background:linear-gradient(135deg,#3b82f6,#06b6d4);
                border-radius:8px; display:flex; align-items:center; justify-content:center;">
        <span style="font-size:16px;">🚕</span>
    </div>
    <div>
        <div style="font-size:16px; font-weight:600; color:#f1f5f9;">NYC Taxi Supply-Demand Intelligence</div>
        <div style="font-size:11px; color:#64748b;">2023 TLC Yellow Taxi (Jan–Dec, full year) · H3 Res 8 · PostGIS + dbt + Streamlit</div>
    </div>
</div>
""", unsafe_allow_html=True)

# KPI Bar
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">💰 Revenue Loss</div><div class="kpi-value">${total_loss/1e6:.1f}M</div><div class="kpi-delta down">from undersupplied zones only</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">📍 Zones Analyzed</div><div class="kpi-value">{len(df)}</div><div class="kpi-delta neutral">H3 res-8 cells, ≥500 trips/yr</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">🔴 Supply Gap Zones</div><div class="kpi-value">{len(undersupplied)}</div><div class="kpi-delta down">{len(undersupplied)/len(df)*100:.0f}% of all zones</div></div>', unsafe_allow_html=True)
with k4:
    if len(undersupplied) > 0:
        worst = undersupplied.iloc[0]
        wn = worst['zone_name']
        wl = worst['estimated_revenue_loss_usd']
        wpct = wl / total_loss * 100
        wur = worst['unmet_demand_rate']
        st.markdown(
            f'<div class="kpi-card" style="border-left:3px solid #ef4444; background:#1a0f0f;">'
            f'<div class="kpi-label" style="color:#f87171;">🎯 1 Zone = {wpct:.0f}% of Total Loss</div>'
            f'<div class="kpi-value" style="font-size:19px;">{wn}</div>'
            f'<div class="kpi-delta down">${wl/1e6:.1f}M · {wur:.0%} unmet</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div class="kpi-card"><div class="kpi-label">Worst Zone</div><div class="kpi-value">—</div></div>', unsafe_allow_html=True)
with k5:
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">🔵 Oversupplied</div><div class="kpi-value">{len(oversupplied)}</div><div class="kpi-delta neutral">{len(oversupplied)/len(df)*100:.0f}% — fleet rebalance needed</div></div>', unsafe_allow_html=True)

st.markdown('<div style="font-size:11px; color:#64748b; margin-top:8px; padding:6px 12px; background:#111827; border:1px solid #1e2433; border-radius:6px; display:inline-block;">📊 Data: NYC TLC Yellow Taxi Trip Records · Jan 1 – Dec 31, 2023 · 12 months · Source: NYC TLC Trip Record Data (CloudFront)</div>', unsafe_allow_html=True)
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)
status_filter = st.sidebar.multiselect("Zone Status", ["UNDERSUPPLIED", "BALANCED", "OVERSUPPLIED"], default=["UNDERSUPPLIED", "BALANCED", "OVERSUPPLIED"])
boroughs = ["All"] + sorted(df['borough'].dropna().unique().tolist())
selected_borough = st.sidebar.selectbox("Borough", boroughs)
filtered = df[df['zone_status'].isin(status_filter)]
if selected_borough != "All":
    filtered = filtered[filtered['borough'] == selected_borough]
st.sidebar.markdown(f"**{len(filtered)}** of {len(df)} zones shown")

st.sidebar.markdown('<div class="section-title" style="margin-top:20px;">Zone Status Breakdown</div>', unsafe_allow_html=True)
for status, (color, count) in {'UNDERSUPPLIED': ('#dc2626', len(undersupplied)), 'BALANCED': ('#eab308', len(balanced)), 'OVERSUPPLIED': ('#1e78dc', len(oversupplied))}.items():
    pct = count / len(df) * 100
    st.sidebar.markdown(f'<div class="status-row"><div class="status-dot" style="background:{color};"></div><div class="status-name">{status.title()}</div><div class="status-count">{count}</div></div><div class="status-bar-bg"><div class="status-bar-fill" style="width:{pct}%; background:{color};"></div></div>', unsafe_allow_html=True)

st.sidebar.markdown('<div class="section-title" style="margin-top:20px;">Revenue Loss by Borough</div>', unsafe_allow_html=True)
borough_loss = undersupplied.groupby('borough')['estimated_revenue_loss_usd'].sum().sort_values(ascending=False)
if not borough_loss.empty:
    mx = borough_loss.max()
    for boro, val in borough_loss.items():
        pct = val / mx * 100
        c = '#dc2626' if val > 10e6 else '#f59e0b' if val > 1e6 else '#3b82f6'
        st.sidebar.markdown(f'<div style="margin-bottom:10px;"><div style="display:flex;justify-content:space-between;margin-bottom:3px;"><span style="font-size:12px;color:#cbd5e1;">{boro}</span><span style="font-size:12px;font-weight:600;color:{c};">${val/1e6:.1f}M</span></div><div style="height:6px;background:#1e2433;border-radius:3px;overflow:hidden;"><div style="height:100%;width:{pct}%;background:{c};border-radius:3px;"></div></div></div>', unsafe_allow_html=True)
        
    if 'Queens' in borough_loss.index:
        st.sidebar.markdown(
            '<div style="font-size:11px; color:#94a3b8; padding:8px 10px; '
            'background:#111827; border-left:2px solid #f59e0b; border-radius:4px; '
            'margin-top:4px; line-height:1.5;">'
            '<b style="color:#fbbf24;">Queens &gt; Manhattan?</b> Airport effect. '
            'JFK ($26.3M) + LGA ($15.0M) = $41.3M of Queens total.'
            '</div>',
            unsafe_allow_html=True
        )

st.sidebar.markdown('<div class="section-title" style="margin-top:20px;">Map Color Guide</div>')



# Main: Map + Insights
# Main: Map + Insights
st.markdown(
    '<div style="background:#1a1f2e; border-left:4px solid #ef4444; padding:14px 18px; '
    'border-radius:6px; margin-bottom:16px;">'
    '<div style="font-size:15px; color:#f1f5f9; font-weight:500; margin-bottom:4px;">'
    "It's not a shortage — the taxis are in the wrong places."
    '</div>'
    '<div style="font-size:12px; color:#94a3b8;">'
    f'{len(oversupplied)} of {len(df)} zones ({len(oversupplied)/len(df)*100:.0f}%) are oversupplied. '
    f'Only {len(undersupplied)} zones ({len(undersupplied)/len(df)*100:.0f}%) are undersupplied — '
    f'yet they account for ${total_loss/1e6:.1f}M/year in lost revenue. Fleet misallocation, not scarcity.'
    '</div>'
    '</div>',
    unsafe_allow_html=True
)

map_col, insight_col = st.columns([3, 1])

STATUS_COLORS = {
    "UNDERSUPPLIED": [220, 30, 30, 200],
    "BALANCED":      [234, 179, 8, 160],
    "OVERSUPPLIED":  [30, 120, 220, 100]
}

# 2D — flat list of dicts, geometry sebagai field (bukan GeoJSON FeatureCollection)
features_2d = []
for _, row in filtered.iterrows():
    if not row['geom_json']:
        continue
    color = STATUS_COLORS.get(row['zone_status'], [128, 128, 128, 100])
    features_2d.append({
        "geometry":     json.loads(row['geom_json']),
        "zone":         row['zone_name'] or "Unknown",
        "borough":      row['borough'] or "Unknown",
        "status":       row['zone_status'],
        "revenue_loss": f"${float(row['estimated_revenue_loss_usd'] or 0):,.0f}",
        "unmet_rate":   f"{float(row['unmet_demand_rate'] or 0):.1%}",
        "ratio":        f"{float(row['supply_demand_ratio'] or 0):.2f}",
        "road_segs":    int(row['road_segment_count'] or 0),
        "fill_color":   color,
    })

layer_2d = pdk.Layer(
    "GeoJsonLayer",
    data=features_2d,          # list of dicts, bukan FeatureCollection
    stroked=True,
    filled=True,
    extruded=False,
    get_fill_color="fill_color",
    get_line_color=[255, 255, 255, 40],
    get_line_width=20,
    pickable=True,
    auto_highlight=True,
    highlight_color=[255, 255, 255, 50],
)

# Tooltip 2D — flat fields, TANPA properties.
tooltip_2d = {
    "html": """<div style='font-family:sans-serif;font-size:13px;'>
        <b style='font-size:14px'>{zone}</b><br/>
        <span style='color:#94a3b8'>Borough:</span> {borough}<br/>
        <span style='color:#94a3b8'>Status:</span> <b>{status}</b><br/>
        <span style='color:#94a3b8'>S/D Ratio:</span> {ratio}<br/>
        <span style='color:#94a3b8'>Revenue Loss:</span> <b style='color:#f87171'>{revenue_loss}</b><br/>
        <span style='color:#94a3b8'>Unmet Rate:</span> {unmet_rate}<br/>
        <span style='color:#94a3b8'>Road Segments:</span> {road_segs}
    </div>""",
    "style": {
        "backgroundColor": "#1a1f2e",
        "color": "#e2e8f0",
        "borderRadius": "8px",
        "padding": "10px",
        "border": "1px solid #2d3748"
    }
}

tooltip_3d = {
    "html": """<div style='font-family:sans-serif;font-size:13px;'>
        <b style='font-size:14px'>{zone}</b><br/>
        <span style='color:#94a3b8'>Borough:</span> {borough}<br/>
        <span style='color:#94a3b8'>Revenue Loss:</span> <b style='color:#f87171'>{revenue_loss}</b><br/>
        <span style='color:#94a3b8'>Unmet Rate:</span> {unmet_rate}<br/>
        <span style='color:#94a3b8'>Road Segments:</span> {road_segs}
    </div>""",
    "style": {
        "backgroundColor": "#1a1f2e",
        "color": "#e2e8f0",
        "borderRadius": "8px",
        "padding": "10px"
    }
}
with map_col:
    view_mode = st.radio("Map View", ["2D Overview", "3D Revenue Loss"], horizontal=True, label_visibility="collapsed")

    if view_mode == "3D Revenue Loss":
        hex_data = []
        mx = undersupplied['estimated_revenue_loss_usd'].max()
        for _, row in undersupplied.iterrows():
            loss = float(row['estimated_revenue_loss_usd'] or 0)
            intensity = loss / mx if mx > 0 else 0
            hex_data.append({
                "hex": row['h3_cell'],
                "elevation": intensity * 4500,
                "color": [220, 38, 38, 220],
                "zone": row['zone_name'],
                "borough": row['borough'],
                "revenue_loss": f"${loss:,.0f}",
                "unmet_rate": f"{float(row['unmet_demand_rate'] or 0):.1%}",
                "road_segs": int(row['road_segment_count'] or 0),
            })

        active_layer = pdk.Layer(
            "H3HexagonLayer",
            data=hex_data,
            get_hexagon="hex",
            get_elevation="elevation",
            elevation_scale=1,
            extruded=True,
            get_fill_color="color",
            pickable=True,
            auto_highlight=True,
        )
        active_tooltip = tooltip_3d
        view = pdk.ViewState(latitude=40.72, longitude=-73.95,
                             zoom=10, pitch=55, bearing=-20)
        st.caption("Taller = more revenue lost. 13 undersupplied zones only.")
    else:
        active_layer = layer_2d
        active_tooltip = tooltip_2d
        view = pdk.ViewState(latitude=40.7128, longitude=-74.006, zoom=10, pitch=0)

    st.pydeck_chart(pdk.Deck(layers=[active_layer], initial_view_state=view,
        tooltip=active_tooltip,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"), height=520)

with insight_col:
    st.markdown('<div class="section-title">Key Findings</div>', unsafe_allow_html=True)
    st.markdown('<div class="finding-item high"><div class="finding-title">Fleet Misallocation</div><div class="finding-desc">159 zones oversupplied while 13 zones lose $81.6M/yr. Not a shortage — taxis are in the wrong place.</div><span class="finding-badge high">Critical</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="finding-item high"><div class="finding-title">JFK Airport Dominance</div><div class="finding-desc">JFK alone accounts for ${undersupplied.iloc[0]["estimated_revenue_loss_usd"]/1e6:.1f}M — {undersupplied.iloc[0]["estimated_revenue_loss_usd"]/total_loss*100:.0f}% of all revenue loss. Unmet rate: {undersupplied.iloc[0]["unmet_demand_rate"]:.0%}.</div><span class="finding-badge high">High Priority</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="finding-item med"><div class="finding-title">Penn Station Catchment</div><div class="finding-desc">Garment District (within 800m of Penn Station) has $11.4M undersupply. Commuter exit zone.</div><span class="finding-badge med">Medium</span></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="finding-item med">'
        '<div class="finding-title">Marble Hill — Boundary Mismatch Detected</div>'
        '<div class="finding-desc">Detected via ST_Within spatial join: TLC labels this zone as '
        'Manhattan, but geometry places it inside Bronx polygon. Root cause: 1895 Harlem Ship '
        'Canal realignment. Data quality issue surfaced by spatial reasoning, not aggregation. '
        'Revenue impact $0 — significance is methodological.</div>'
        '<span class="finding-badge med">Spatial Validation</span>'
        '</div>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="section-title" style="margin-top:16px;">Spatial Validation</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:12px;color:#94a3b8;line-height:1.8;">✅ 181/185 zones matched borough polygon<br>✅ 180/181 label-to-spatial match correct<br>⚠️ 1 known anomaly (Marble Hill)<br>⚠️ 4 zones on water/boundary edge ($0 loss)</div>', unsafe_allow_html=True)

# How to Read
with st.expander("📖 How to read this dashboard", expanded=True):
    st.markdown(f"""
<div style="color:#e2e8f0; font-size:14px; line-height:1.7;">

<div style="font-size:16px; color:#f1f5f9; font-weight:600; margin-bottom:8px;">The Story</div>
<p style="color:#cbd5e1; margin-bottom:16px;">
NYC has <b style="color:#f1f5f9;">{len(df)} active taxi zones</b> (H3 resolution 8, minimum 500 trips/year).
Of these, <b style="color:#f87171;">{len(undersupplied)} are genuinely undersupplied</b> — demand exceeds supply,
causing an estimated <b style="color:#f87171;">${total_loss/1e6:.1f}M/year</b> in lost revenue.
Meanwhile, <b style="color:#60a5fa;">{len(oversupplied)} zones are oversupplied</b> — taxis idle while nearby zones go unserved.
This is a <b style="color:#f1f5f9;">fleet misallocation problem</b>, not a shortage.
</p>

<div style="font-size:16px; color:#f1f5f9; font-weight:600; margin-bottom:8px;">Map Views</div>
<ul style="color:#cbd5e1; padding-left:20px; margin-bottom:16px;">
<li style="margin-bottom:4px;"><b style="color:#f1f5f9;">2D Overview</b>: all {len(df)} zones colored by status (red/yellow/blue)</li>
<li style="margin-bottom:4px;"><b style="color:#f1f5f9;">3D Revenue Loss</b>: only undersupplied zones, column height = revenue loss magnitude</li>
</ul>

<div style="font-size:16px; color:#f1f5f9; font-weight:600; margin-bottom:8px;">Metrics</div>
<ul style="color:#cbd5e1; padding-left:20px;">
<li style="margin-bottom:4px;"><b style="color:#f1f5f9;">Supply/Demand Ratio</b>: &lt;0.9 = undersupplied, 0.9–1.1 = balanced, &gt;1.1 = oversupplied</li>
<li style="margin-bottom:4px;"><b style="color:#f1f5f9;">Unmet Demand Rate</b>: share of trips not served (0–1, undersupplied zones only)</li>
<li style="margin-bottom:4px;"><b style="color:#f1f5f9;">Revenue Loss</b>: unmet trips × $18.50 avg fare (lower-bound estimate)</li>
</ul>

</div>
    """, unsafe_allow_html=True)

# Zone Detail Table
st.markdown('<div class="section-title">Zone Detail Table</div>', unsafe_allow_html=True)
display = filtered[['zone_name','borough','zone_status','total_demand_trips','total_supply_trips','supply_demand_ratio','unmet_demand_rate','road_segment_count','estimated_revenue_loss_usd']].copy()
display.columns = ['Zone','Borough','Status','Demand (trips)','Supply (trips)','S/D Ratio','Unmet Rate','Road Segments','Revenue Loss (USD)']
display['Unmet Rate'] = display['Unmet Rate'].apply(lambda x: f"{x:.1%}")
display['S/D Ratio'] = display['S/D Ratio'].apply(lambda x: f"{x:.2f}")
display['Revenue Loss (USD)'] = display['Revenue Loss (USD)'].apply(lambda x: f"${x:,.0f}")
st.dataframe(display, use_container_width=True, hide_index=True, height=300)

# Transit Hub Analysis
st.markdown('<div class="section-title" style="margin-top:16px;">🚇 Undersupplied Zones Near Transit Hubs (800m Walking Radius)</div><div style="font-size:12px;color:#64748b;margin-bottom:12px;">Highest priority for fleet redeployment: high foot traffic + unmet taxi demand.</div>', unsafe_allow_html=True)
transit_df = load_transit()
if not transit_df.empty:
    transit_df.columns = ['Transit Hub','Zone','Borough','Revenue Loss (USD)','Distance (m)']
    transit_df['Revenue Loss (USD)'] = transit_df['Revenue Loss (USD)'].apply(lambda x: f"${float(x):,.0f}")
    st.dataframe(transit_df, use_container_width=True, hide_index=True)
else:
    st.info("No undersupplied zones within 800m of transit hubs.")

# Road Finding Analysis — full section
st.markdown('<div class="section-title" style="margin-top:16px;">🛣️ OSM Road Density — Is Access the Bottleneck?</div>', unsafe_allow_html=True)

road_stats = df.groupby('zone_status')['road_segment_count'].mean().round(1)

rc1, rc2 = st.columns([1, 1])

with rc1:
    st.markdown(
        '<div style="background:#1a1f2e; border-left:4px solid #ef4444; padding:16px 18px; '
        'border-radius:6px; margin-bottom:12px;">'
        '<div style="font-size:15px; color:#f1f5f9; font-weight:500; margin-bottom:6px;">'
        'Road access is not the constraint.'
        '</div>'
        '<div style="font-size:13px; color:#94a3b8; line-height:1.6;">'
        f'Undersupplied zones average <b style="color:#f1f5f9;">{road_stats.get("UNDERSUPPLIED", 0):.1f} road segments</b> — '
        f'<i>more</i> than oversupplied zones at <b style="color:#f1f5f9;">{road_stats.get("OVERSUPPLIED", 0):.1f}</b>. '
        'If infrastructure were the bottleneck, undersupplied zones would show fewer roads, not more. '
        'This rules out physical accessibility and strengthens the case for fleet misallocation: '
        'taxis are avoiding zones that are demonstrably easy to reach.'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="finding-item high">'
        '<div class="finding-title">LaGuardia — the exception that proves the rule</div>'
        '<div class="finding-desc">Only 9 road segments — the most road-constrained zone in the dataset — '
        'yet still undersupplied, losing $15.0M/yr (65.7% unmet). Even the zone with the weakest '
        'physical case for more taxis is being underserved. Dispatch and positioning, not roads, '
        'are the root cause.</div>'
        '<span class="finding-badge high">Root Cause: Dispatch</span>'
        '</div>',
        unsafe_allow_html=True
    )

with rc2:
    import plotly.express as px
    color_map = {"UNDERSUPPLIED": "#ef4444", "BALANCED": "#eab308", "OVERSUPPLIED": "#1e78dc"}
    order = ["OVERSUPPLIED", "BALANCED", "UNDERSUPPLIED"]

    fig = px.box(
        df, x='zone_status', y='road_segment_count', color='zone_status',
        color_discrete_map=color_map, category_orders={'zone_status': order},
        points='all', hover_data=['zone_name'],
        labels={'zone_status': '', 'road_segment_count': 'Road Segments'},
    )
    fig.update_traces(
        marker=dict(size=5, opacity=0.6),
        line=dict(width=1.5),
    )
    fig.update_layout(
        plot_bgcolor='#0f1117', paper_bgcolor='#0f1117',
        font=dict(color='#94a3b8', size=11),
        margin=dict(l=10, r=10, t=10, b=10), height=380,
        showlegend=False,
        xaxis=dict(gridcolor='#1e2433', zerolinecolor='#1e2433'),
        yaxis=dict(gridcolor='#1e2433', zerolinecolor='#1e2433'),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Road segment distribution by zone status. Undersupplied zones (red) are NOT lower — median sits above oversupplied (blue).")

# Footer
# Pipeline Architecture — DE positioning section
st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
st.markdown(
    '<div style="border-top:1px solid #1e2433; padding-top:20px;">'
    '<div class="section-title" style="font-size:12px;">🔧 How This Was Built — Production Data Engineering Stack</div>'
    '<div style="font-size:14px; color:#cbd5e1; line-height:1.6; margin-bottom:20px; max-width:900px;">'
    'Not a Jupyter notebook. A production pipeline: <b style="color:#f1f5f9;">38.3M rows</b> processed, '
    '<b style="color:#f1f5f9;">5-layer stack</b>, infrastructure-as-code, orchestrated end-to-end. '
    'Every layer below reflects a design decision documented in '
    '<a href="https://github.com/mahardisetyoso/nyc_taxi_supply_demand_analysis/blob/main/DECISIONS.md" '
    'target="_blank" style="color:#60a5fa;">DECISIONS.md</a>.'
    '</div>'
    '</div>',
    unsafe_allow_html=True
)

# Row 1a: System Architecture (SVG, wider — needs breathing room for text)
st.markdown('<div style="font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px;">System Architecture — 6-layer stack, one region</div>', unsafe_allow_html=True)
arch_l, arch_c, arch_r = st.columns([1, 6, 1])
with arch_c:
    st.image("asset/architecture.svg", use_container_width=True)

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

# Row 1b: Data Flow GIF (portrait aspect, centered narrower)
st.markdown('<div style="font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px;">Data Flow — one NYC taxi trip end-to-end</div>', unsafe_allow_html=True)
gif_l, gif_c, gif_r = st.columns([1, 2, 1])
with gif_c:
    st.image("asset/post4_nyc_taxi_pipeline.gif", use_container_width=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# Row 2: Stack breakdown — 5 columns matching pipeline layers
st.markdown('<div style="font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:12px;">Stack by Layer</div>', unsafe_allow_html=True)

s1, s2, s3, s4, s5 = st.columns(5)

STACK_CARD_STYLE = 'background:#111827; border:1px solid #1e2433; border-radius:8px; padding:12px 14px; height:100%;'

with s1:
    st.markdown(
        f'<div style="{STACK_CARD_STYLE}">'
        '<div style="font-size:10px; color:#60a5fa; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">1 · Orchestration</div>'
        '<div style="font-size:14px; color:#f1f5f9; font-weight:500; margin-bottom:4px;">Kestra</div>'
        '<div style="font-size:11px; color:#94a3b8; line-height:1.5;">Docker Compose · 4 flows · trigger.date backfill</div>'
        '</div>',
        unsafe_allow_html=True
    )
with s2:
    st.markdown(
        f'<div style="{STACK_CARD_STYLE}">'
        '<div style="font-size:10px; color:#60a5fa; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">2 · Storage</div>'
        '<div style="font-size:14px; color:#f1f5f9; font-weight:500; margin-bottom:4px;">GCS + BigQuery</div>'
        '<div style="font-size:11px; color:#94a3b8; line-height:1.5;">Parquet lake · 2 datasets · asia-southeast1</div>'
        '</div>',
        unsafe_allow_html=True
    )
with s3:
    st.markdown(
        f'<div style="{STACK_CARD_STYLE}">'
        '<div style="font-size:10px; color:#60a5fa; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">3 · Compute</div>'
        '<div style="font-size:14px; color:#f1f5f9; font-weight:500; margin-bottom:4px;">Dataproc + PySpark</div>'
        '<div style="font-size:11px; color:#94a3b8; line-height:1.5;">1 master + 2 workers · ~3 min · H3 res-8</div>'
        '</div>',
        unsafe_allow_html=True
    )
with s4:
    st.markdown(
        f'<div style="{STACK_CARD_STYLE}">'
        '<div style="font-size:10px; color:#60a5fa; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">4 · Modeling</div>'
        '<div style="font-size:14px; color:#f1f5f9; font-weight:500; margin-bottom:4px;">dbt on BigQuery</div>'
        '<div style="font-size:11px; color:#94a3b8; line-height:1.5;">4 marts · 10 tests · rate-of-totals guardrails</div>'
        '</div>',
        unsafe_allow_html=True
    )
with s5:
    st.markdown(
        f'<div style="{STACK_CARD_STYLE}">'
        '<div style="font-size:10px; color:#60a5fa; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">5 · Serving</div>'
        '<div style="font-size:14px; color:#f1f5f9; font-weight:500; margin-bottom:4px;">Supabase + Streamlit</div>'
        '<div style="font-size:11px; color:#94a3b8; line-height:1.5;">PostGIS 3.3 · pydeck · Plotly</div>'
        '</div>',
        unsafe_allow_html=True
    )

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# Row 3: Production metrics — 3 wide KPI cards
st.markdown('<div style="font-size:11px; color:#64748b; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:12px;">Production Metrics</div>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)

METRIC_CARD_STYLE = 'background:#111827; border:1px solid #1e2433; border-radius:8px; padding:14px 16px;'

with m1:
    st.markdown(
        f'<div style="{METRIC_CARD_STYLE} border-left:3px solid #3b82f6;">'
        '<div style="font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">Infrastructure-as-Code</div>'
        '<div style="font-size:18px; color:#f1f5f9; font-weight:600; margin-bottom:4px;">Terraform</div>'
        '<div style="font-size:11px; color:#94a3b8; line-height:1.5;">GCS bucket + 2 BQ datasets + service account provisioned in code. Zero click-ops.</div>'
        '</div>',
        unsafe_allow_html=True
    )
with m2:
    st.markdown(
        f'<div style="{METRIC_CARD_STYLE} border-left:3px solid #3b82f6;">'
        '<div style="font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">Data Volume</div>'
        '<div style="font-size:18px; color:#f1f5f9; font-weight:600; margin-bottom:4px;">38.3M rows processed</div>'
        '<div style="font-size:11px; color:#94a3b8; line-height:1.5;">12 months TLC Yellow Taxi 2023 → 34.96M enriched with H3 res-8 · 72,005 OSM road segments joined via ST_Intersects.</div>'
        '</div>',
        unsafe_allow_html=True
    )
with m3:
    st.markdown(
        f'<div style="{METRIC_CARD_STYLE} border-left:3px solid #f59e0b;">'
        '<div style="font-size:10px; color:#64748b; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">Schema Evolution Handled</div>'
        '<div style="font-size:18px; color:#f1f5f9; font-weight:600; margin-bottom:4px;">7 columns drift</div>'
        '<div style="font-size:11px; color:#94a3b8; line-height:1.5;">Jan 2023 legacy schema detected via <code style="background:#0f1117;padding:1px 5px;border-radius:3px;color:#e2e8f0;">schema_diff.py</code>. Per-file cast + unionByName fix.</div>'
        '</div>',
        unsafe_allow_html=True
    )

# Footer
st.markdown('<div style="text-align:center;padding:24px 0 12px;border-top:1px solid #1e2433;margin-top:32px;"><span style="font-size:12px;color:#64748b;">Mahardi Setyoso · NYC TLC 2023 · H3 + PostGIS + dbt + Streamlit</span></div>', unsafe_allow_html=True)