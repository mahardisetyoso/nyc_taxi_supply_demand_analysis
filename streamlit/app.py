import streamlit as st
import psycopg2
import pandas as pd
import pydeck as pdk
import os
import json

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Page Config
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(
    page_title="GeoOps · NYC Taxi Supply-Demand",
    page_icon="🚕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Custom CSS — dark theme matching reference layout
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
<style>
    /* Dark background */
    .stApp { background-color: #0f1117; }
    section[data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #1e2433; }

    /* KPI cards */
    .kpi-card {
        background: #111827;
        border: 1px solid #1e2433;
        border-radius: 8px;
        padding: 16px 18px;
        text-align: left;
    }
    .kpi-label {
        font-size: 11px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 24px;
        font-weight: 600;
        color: #f1f5f9;
        line-height: 1.2;
    }
    .kpi-delta {
        font-size: 11px;
        margin-top: 4px;
    }
    .kpi-delta.up { color: #34d399; }
    .kpi-delta.down { color: #f87171; }
    .kpi-delta.neutral { color: #64748b; }

    /* Anomaly feed items */
    .finding-item {
        background: #111827;
        border: 1px solid #1e2433;
        border-left: 3px solid;
        border-radius: 6px;
        padding: 10px 12px;
        margin-bottom: 8px;
    }
    .finding-item.high { border-left-color: #ef4444; }
    .finding-item.med { border-left-color: #f59e0b; }
    .finding-item.low { border-left-color: #3b82f6; }
    .finding-title { font-size: 13px; color: #e2e8f0; font-weight: 500; }
    .finding-desc { font-size: 11px; color: #94a3b8; margin-top: 3px; }
    .finding-badge {
        display: inline-block;
        font-size: 10px;
        padding: 2px 7px;
        border-radius: 3px;
        margin-top: 5px;
    }
    .finding-badge.high { background: #3f1010; color: #f87171; }
    .finding-badge.med { background: #3f2a10; color: #fbbf24; }
    .finding-badge.low { background: #1e3a5f; color: #60a5fa; }

    /* Section headers */
    .section-title {
        font-size: 11px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 12px;
        padding-bottom: 6px;
        border-bottom: 1px solid #1e2433;
    }

    /* Status pills */
    .status-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 10px;
        background: #111827;
        border: 1px solid #1e2433;
        border-radius: 6px;
        margin-bottom: 6px;
    }
    .status-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .status-name { font-size: 13px; color: #cbd5e1; flex: 1; }
    .status-count { font-size: 12px; color: #64748b; }
    .status-bar-bg {
        height: 3px;
        background: #1e2433;
        border-radius: 2px;
        margin-top: 4px;
        width: 100%;
    }
    .status-bar-fill { height: 3px; border-radius: 2px; }

    /* Hide Streamlit defaults */
    #MainMenu { visibility: hidden; }
    header[data-testid="stHeader"] { background: #0f1117; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data Loading
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_data(ttl=300)
def load_zones():
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"])
    df = pd.read_sql("""
        SELECT zone_name, borough, h3_cell, zone_status,
            total_demand_trips, total_supply_trips,
            supply_demand_ratio, unmet_demand_rate, oversupply_ratio,
            estimated_revenue_loss_usd, estimated_unmet_trips,
            ST_AsGeoJSON(geom) AS geom_json
        FROM revenue_loss_by_zone
        WHERE geom IS NOT NULL
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
            ROUND(ST_Distance(
                r.geom::geography,
                ST_SetSRID(ST_MakePoint(hub.lng, hub.lat), 4326)::geography
            )::numeric, 0) AS distance_meters
        FROM revenue_loss_by_zone r
        CROSS JOIN (VALUES
            ('Penn Station',     -73.9934, 40.7506),
            ('Grand Central',    -73.9772, 40.7527),
            ('Port Authority',   -73.9903, 40.7571),
            ('Union Square',     -73.9897, 40.7359),
            ('JFK AirTrain Hub', -73.7789, 40.6413)
        ) AS hub(name, lng, lat)
        WHERE r.zone_status = 'UNDERSUPPLIED'
          AND ST_Within(
            ST_Centroid(r.geom),
            ST_Buffer(
                ST_SetSRID(ST_MakePoint(hub.lng, hub.lat), 4326)::geography, 800
            )::geometry
          )
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Header
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
    <div style="width:32px; height:32px; background:linear-gradient(135deg,#3b82f6,#06b6d4);
                border-radius:8px; display:flex; align-items:center; justify-content:center;">
        <span style="font-size:16px;">🚕</span>
    </div>
    <div>
        <div style="font-size:16px; font-weight:600; color:#f1f5f9;">
            NYC Taxi Supply-Demand Intelligence
        </div>
        <div style="font-size:11px; color:#64748b;">
            2023 TLC Yellow Taxi (Jan–Dec, full year) · H3 Res 8 · PostGIS + dbt + Streamlit
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KPI Bar — 5 metrics across top
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">💰 Revenue Loss</div>
        <div class="kpi-value">${total_loss/1e6:.1f}M</div>
        <div class="kpi-delta down">from undersupplied zones only</div>
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">📍 Zones Analyzed</div>
        <div class="kpi-value">{len(df)}</div>
        <div class="kpi-delta neutral">H3 res-8 cells, ≥500 trips/yr</div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">🔴 Supply Gap Zones</div>
        <div class="kpi-value">{len(undersupplied)}</div>
        <div class="kpi-delta down">{len(undersupplied)/len(df)*100:.0f}% of all zones</div>
    </div>""", unsafe_allow_html=True)

with k4:
    worst = undersupplied.iloc[0] if len(undersupplied) > 0 else None
    worst_name = worst['zone_name'] if worst is not None else "—"
    worst_loss = worst['estimated_revenue_loss_usd'] if worst is not None else 0
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">⚠️ Worst Zone</div>
        <div class="kpi-value" style="font-size:18px;">{worst_name}</div>
        <div class="kpi-delta down">${worst_loss/1e6:.1f}M lost</div>
    </div>""", unsafe_allow_html=True)

with k5:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">🔵 Oversupplied</div>
        <div class="kpi-value">{len(oversupplied)}</div>
        <div class="kpi-delta neutral">{len(oversupplied)/len(df)*100:.0f}% — fleet rebalance needed</div>
    </div>""", unsafe_allow_html=True)

st.markdown("""
<div style="font-size:11px; color:#64748b; margin-top:8px; padding:6px 12px;
            background:#111827; border:1px solid #1e2433; border-radius:6px;
            display:inline-block;">
    📊 Data: NYC TLC Yellow Taxi Trip Records · Jan 1 – Dec 31, 2023 · 12 months · Source: NYC Open Data
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Sidebar — Filters + Breakdown + Findings
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.sidebar.markdown('<div class="section-title">Filters</div>', unsafe_allow_html=True)

status_filter = st.sidebar.multiselect(
    "Zone Status",
    ["UNDERSUPPLIED", "BALANCED", "OVERSUPPLIED"],
    default=["UNDERSUPPLIED", "BALANCED", "OVERSUPPLIED"]
)
boroughs = ["All"] + sorted(df['borough'].dropna().unique().tolist())
selected_borough = st.sidebar.selectbox("Borough", boroughs)

filtered = df[df['zone_status'].isin(status_filter)]
if selected_borough != "All":
    filtered = filtered[filtered['borough'] == selected_borough]

st.sidebar.markdown(f"**{len(filtered)}** of {len(df)} zones shown")

# --- Zone Status Breakdown ---
st.sidebar.markdown('<div class="section-title" style="margin-top:20px;">Zone Status Breakdown</div>',
                    unsafe_allow_html=True)

status_config = {
    'UNDERSUPPLIED': ('#dc2626', len(undersupplied)),
    'BALANCED':      ('#eab308', len(balanced)),
    'OVERSUPPLIED':  ('#1e78dc', len(oversupplied)),
}
for status, (color, count) in status_config.items():
    pct = count / len(df) * 100
    st.sidebar.markdown(f"""
    <div class="status-row">
        <div class="status-dot" style="background:{color};"></div>
        <div class="status-name">{status.title()}</div>
        <div class="status-count">{count}</div>
    </div>
    <div class="status-bar-bg">
        <div class="status-bar-fill" style="width:{pct}%; background:{color};"></div>
    </div>
    """, unsafe_allow_html=True)

# --- Revenue by Borough ---
st.sidebar.markdown('<div class="section-title" style="margin-top:20px;">Revenue Loss by Borough</div>',
                    unsafe_allow_html=True)

borough_loss = (undersupplied.groupby('borough')['estimated_revenue_loss_usd']
                .sum().sort_values(ascending=False))
if not borough_loss.empty:
    max_val = borough_loss.max()
    for boro, val in borough_loss.items():
        pct = val / max_val * 100
        color = '#dc2626' if val > 10e6 else '#f59e0b' if val > 1e6 else '#3b82f6'
        st.sidebar.markdown(f"""
        <div style="margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                <span style="font-size:12px; color:#cbd5e1;">{boro}</span>
                <span style="font-size:12px; font-weight:600; color:{color};">${val/1e6:.1f}M</span>
            </div>
            <div style="height:6px; background:#1e2433; border-radius:3px; overflow:hidden;">
                <div style="height:100%; width:{pct}%; background:{color}; border-radius:3px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- Color Guide ---
st.sidebar.markdown("""
<div class="section-title" style="margin-top:20px;">Map Color Guide</div>
<div style="font-size:12px; color:#94a3b8; line-height:1.8;">
    🔴 <b style="color:#dc2626">Red</b> — Undersupplied (demand > supply)<br>
    🟡 <b style="color:#eab308">Yellow</b> — Balanced (±10% tolerance)<br>
    🔵 <b style="color:#1e78dc">Blue</b> — Oversupplied (excess supply)<br>
    <span style="color:#64748b; font-size:11px;">Only red zones contribute to revenue loss.</span>
</div>
""", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main: Map (left) + Insights Panel (right)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
map_col, insight_col = st.columns([3, 1])

# --- Map Panel ---
STATUS_COLORS = {
    "UNDERSUPPLIED": [220, 30, 30, 200],
    "BALANCED":      [234, 179, 8, 160],
    "OVERSUPPLIED":  [30, 120, 220, 100],
}

features = []
for _, row in filtered.iterrows():
    if not row['geom_json']:
        continue
    loss = float(row['estimated_revenue_loss_usd'] or 0)
    color = STATUS_COLORS.get(row['zone_status'], [128, 128, 128, 100])
    features.append({
        "type": "Feature",
        "geometry": json.loads(row['geom_json']),
        "properties": {
            "zone": row['zone_name'] or "Unknown",
            "borough": row['borough'] or "Unknown",
            "status": row['zone_status'],
            "revenue_loss": f"${loss:,.0f}",
            "unmet_rate": f"{float(row['unmet_demand_rate'] or 0):.1%}",
            "ratio": f"{float(row['supply_demand_ratio'] or 0):.2f}",
            "fill_color": color,
        }
    })

geojson_data = {"type": "FeatureCollection", "features": features}

layer = pdk.Layer(
    "GeoJsonLayer",
    data=geojson_data,
    stroked=True, filled=True, extruded=False,
    get_fill_color="properties.fill_color",
    get_line_color=[255, 255, 255, 40],
    get_line_width=20,
    pickable=True,
    auto_highlight=True,
)

tooltip = {
    "html": (
        "<div style='font-family:Inter,sans-serif; font-size:13px;'>"
        "<b style='font-size:14px'>{properties.zone}</b><br/>"
        "<span style='color:#94a3b8'>Borough:</span> {properties.borough}<br/>"
        "<span style='color:#94a3b8'>Status:</span> <b>{properties.status}</b><br/>"
        "<span style='color:#94a3b8'>S/D Ratio:</span> {properties.ratio}<br/>"
        "<span style='color:#94a3b8'>Revenue Loss:</span> "
        "<b style='color:#f87171'>{properties.revenue_loss}</b><br/>"
        "<span style='color:#94a3b8'>Unmet Rate:</span> {properties.unmet_rate}"
        "</div>"
    ),
    "style": {
        "backgroundColor": "#1a1f2e",
        "color": "#e2e8f0",
        "borderRadius": "8px",
        "padding": "10px",
        "border": "1px solid #2d3748"
    }
}

with map_col:
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(
            latitude=40.7128, longitude=-74.006, zoom=10, pitch=0
        ),
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    ), height=520)

# --- Insight Panel (right of map) ---
with insight_col:
    st.markdown('<div class="section-title">Key Findings</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="finding-item high">
        <div class="finding-title">Fleet Misallocation</div>
        <div class="finding-desc">
            159 zones oversupplied while 13 zones lose $81.6M/yr.
            Not a shortage — taxis are in the wrong place.
        </div>
        <span class="finding-badge high">Critical</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="finding-item high">
        <div class="finding-title">JFK Airport Dominance</div>
        <div class="finding-desc">
            JFK alone accounts for ${undersupplied.iloc[0]['estimated_revenue_loss_usd']/1e6:.1f}M
            — {undersupplied.iloc[0]['estimated_revenue_loss_usd']/total_loss*100:.0f}% of all revenue loss.
            Unmet rate: {undersupplied.iloc[0]['unmet_demand_rate']:.0%}.
        </div>
        <span class="finding-badge high">High Priority</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="finding-item med">
        <div class="finding-title">Penn Station Catchment</div>
        <div class="finding-desc">
            Garment District (within 800m of Penn Station)
            has $11.4M undersupply. Commuter exit zone.
        </div>
        <span class="finding-badge med">Medium</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="finding-item low">
        <div class="finding-title">Marble Hill Anomaly</div>
        <div class="finding-desc">
            Labeled Manhattan, spatially within Bronx.
            Administrative vs geographic boundary mismatch
            (Harlem Ship Canal, 1895). Revenue impact: $0.
        </div>
        <span class="finding-badge low">Informational</span>
    </div>
    """, unsafe_allow_html=True)

    # Quick stats in insight panel
    st.markdown('<div class="section-title" style="margin-top:16px;">Spatial Validation</div>',
                unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size:12px; color:#94a3b8; line-height:1.8;">
        ✅ 181/185 zones matched borough polygon<br>
        ✅ 180/181 label-to-spatial match correct<br>
        ⚠️ 1 known anomaly (Marble Hill)<br>
        ⚠️ 4 zones on water/boundary edge ($0 loss)
    </div>
    """, unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# How to Read (expandable)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.expander("📖 How to read this dashboard", expanded=False):
    st.markdown(f"""
    ### The Story
    NYC has **{len(df)} active taxi zones** (H3 resolution 8, minimum 500 trips/year).
    Of these, **{len(undersupplied)} are genuinely undersupplied** — demand exceeds supply,
    causing an estimated **${total_loss/1e6:.1f}M/year** in lost revenue.
    Meanwhile, **{len(oversupplied)} zones are oversupplied** — taxis idle while nearby zones go unserved.
    This is a **fleet misallocation problem**, not a shortage.

    ### Metrics
    - **Supply/Demand Ratio**: <0.9 = undersupplied, 0.9–1.1 = balanced, >1.1 = oversupplied
    - **Unmet Demand Rate**: share of trips not served (0–1, undersupplied zones only)
    - **Revenue Loss**: unmet trips × $18.50 avg fare (lower-bound estimate)

    ### Transit Hub Analysis
    Undersupplied zones within 800m (~10 min walk) of major transit hubs.
    High foot traffic + unmet taxi demand = immediate fleet redeployment opportunity.
    """)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Zone Detail Table
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="section-title">Zone Detail Table</div>', unsafe_allow_html=True)

display = filtered[[
    'zone_name', 'borough', 'zone_status', 'total_demand_trips',
    'total_supply_trips', 'supply_demand_ratio', 'unmet_demand_rate',
    'estimated_revenue_loss_usd'
]].copy()
display.columns = [
    'Zone', 'Borough', 'Status', 'Demand (trips)', 'Supply (trips)',
    'S/D Ratio', 'Unmet Rate', 'Revenue Loss (USD)'
]
display['Unmet Rate'] = display['Unmet Rate'].apply(lambda x: f"{x:.1%}")
display['S/D Ratio'] = display['S/D Ratio'].apply(lambda x: f"{x:.2f}")
display['Revenue Loss (USD)'] = display['Revenue Loss (USD)'].apply(lambda x: f"${x:,.0f}")

st.dataframe(display, use_container_width=True, hide_index=True, height=300)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Transit Hub Analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
<div class="section-title" style="margin-top:16px;">
    🚇 Undersupplied Zones Near Transit Hubs (800m Walking Radius)
</div>
<div style="font-size:12px; color:#64748b; margin-bottom:12px;">
    Highest priority for fleet redeployment: high foot traffic + unmet taxi demand.
</div>
""", unsafe_allow_html=True)

transit_df = load_transit()
if not transit_df.empty:
    transit_df.columns = ['Transit Hub', 'Zone', 'Borough', 'Revenue Loss (USD)', 'Distance (m)']
    transit_df['Revenue Loss (USD)'] = transit_df['Revenue Loss (USD)'].apply(
        lambda x: f"${float(x):,.0f}")
    st.dataframe(transit_df, use_container_width=True, hide_index=True)
else:
    st.info("No undersupplied zones within 800m of transit hubs.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Footer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
<div style="text-align:center; padding:24px 0 12px; border-top:1px solid #1e2433; margin-top:24px;">
    <span style="font-size:12px; color:#64748b;">
        Mahardi Setyoso · NYC TLC 2023 · H3 + PostGIS + dbt + Streamlit
    </span>
</div>
""", unsafe_allow_html=True)