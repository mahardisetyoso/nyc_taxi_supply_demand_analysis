import streamlit as st
import psycopg2
import pandas as pd
import pydeck as pdk
import os
import json

st.set_page_config(page_title="NYC Taxi Supply-Demand Gap", page_icon="🚕", layout="wide")

@st.cache_data(ttl=300)
def load_data():
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"])
    df = pd.read_sql("""
        SELECT zone_name, borough, h3_cell,
            total_demand_trips, total_supply_trips,
            supply_demand_ratio, unmet_demand_rate, oversupply_ratio,
            zone_status, estimated_revenue_loss_usd, estimated_unmet_trips,
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

# --- Header ---
st.title("🚕 NYC Taxi Supply-Demand Gap Analysis")
st.caption("2023 TLC Yellow Taxi · H3 Resolution 8 · PostGIS + dbt + Streamlit")

with st.spinner("Loading..."):
    df = load_data()

undersupplied = df[df['zone_status'] == 'UNDERSUPPLIED']
balanced = df[df['zone_status'] == 'BALANCED']
oversupplied = df[df['zone_status'] == 'OVERSUPPLIED']
total_loss = undersupplied['estimated_revenue_loss_usd'].sum()

# --- KPIs ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Revenue Loss", f"${total_loss/1e6:.1f}M")
col2.metric("Zones Analyzed", f"{len(df)}")
col3.metric("Supply Gap Zones", f"{len(undersupplied)}")
col4.metric("Worst Zone", undersupplied.iloc[0]['zone_name'] if len(undersupplied) > 0 else "—")

st.divider()

# --- Sidebar ---
st.sidebar.header("Filters")
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

st.sidebar.markdown(f"**{len(filtered)} zones** shown")

st.sidebar.divider()
st.sidebar.markdown("""
**Map Color Guide**

🔴 **Red** — Undersupplied  
Supply gap, revenue being lost

🟡 **Yellow** — Balanced  
Supply ≈ demand (±10% tolerance)

🔵 **Blue** — Oversupplied  
More taxis than needed

Only red zones contribute to revenue loss.
""")

# --- How to read ---
with st.expander("📖 How to read this dashboard", expanded=False):
    st.markdown(f"""
    ### The Story
    NYC has **{len(df)} active taxi zones**. Of these, only **{len(undersupplied)} are genuinely undersupplied**
    — demand exceeds supply, causing an estimated **${total_loss/1e6:.1f}M/year** in lost revenue.
    Meanwhile, **{len(oversupplied)} zones are oversupplied** — taxis sitting idle while nearby zones go unserved.
    This is a **fleet misallocation problem**, not a fleet shortage problem.

    ### Map
    Each hexagon = one H3 cell (~0.7 km² at resolution 8).
    - 🔴 **Red** = undersupplied. Demand > supply. Revenue being lost.
    - 🟡 **Yellow** = balanced. Supply within ±10% of demand.
    - 🔵 **Blue** = oversupplied. Supply exceeds demand.

    **Hover** over any hexagon for zone details.

    ### Key Metrics
    - **Unmet Demand Rate**: share of trips not served (0–1). Only applies to undersupplied zones.
    - **Supply/Demand Ratio**: <0.9 undersupplied, 0.9–1.1 balanced, >1.1 oversupplied.
    - **Revenue Loss**: estimated annual loss from unserved trips at $18.50 avg fare.

    ### Transit Hub Table
    Undersupplied zones within 800m (~10 min walk) of a major transit hub.
    These are the **highest-priority zones** for fleet redeployment.
    """)

# --- Build GeoJSON ---
STATUS_COLORS = {
    "UNDERSUPPLIED": [220, 30, 30, 200],   # Red
    "BALANCED":      [255, 210, 0, 160],    # Yellow
    "OVERSUPPLIED":  [30, 120, 220, 100],   # Blue — lower opacity
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

# --- Map ---
st.subheader(f"Zone Map ({len(filtered)} zones)")

layer = pdk.Layer(
    "GeoJsonLayer",
    data=geojson_data,
    stroked=True,
    filled=True,
    extruded=False,
    get_fill_color="properties.fill_color",
    get_line_color=[255, 255, 255, 40],
    get_line_width=20,
    pickable=True,
    auto_highlight=True,
)

view = pdk.ViewState(latitude=40.7128, longitude=-74.006, zoom=10, pitch=0)

tooltip = {
    "html": (
        "<div style='font-family:sans-serif; font-size:13px;'>"
        "<b style='font-size:15px'>{properties.zone}</b><br/>"
        "<span style='color:#aaa'>Borough:</span> {properties.borough}<br/>"
        "<span style='color:#aaa'>Status:</span> <b>{properties.status}</b><br/>"
        "<span style='color:#aaa'>Supply/Demand Ratio:</span> {properties.ratio}<br/>"
        "<span style='color:#aaa'>Revenue Loss:</span> "
        "<b style='color:#ff6b6b'>{properties.revenue_loss}</b><br/>"
        "<span style='color:#aaa'>Unmet Rate:</span> {properties.unmet_rate}"
        "</div>"
    ),
    "style": {
        "backgroundColor": "#1a1a1a",
        "color": "white",
        "borderRadius": "6px",
        "padding": "10px",
    }
}

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view,
    tooltip=tooltip,
    map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
))

# --- Table ---
st.subheader("Zone Detail Table")
display = filtered[[
    'zone_name','borough','zone_status','total_demand_trips',
    'total_supply_trips','supply_demand_ratio','unmet_demand_rate',
    'estimated_revenue_loss_usd'
]].copy()
display.columns = [
    'Zone','Borough','Status','Demand (trips)','Supply (trips)',
    'S/D Ratio','Unmet Rate','Revenue Loss (USD)'
]
display['Unmet Rate'] = display['Unmet Rate'].apply(lambda x: f"{x:.1%}")
display['S/D Ratio'] = display['S/D Ratio'].apply(lambda x: f"{x:.2f}")
display['Revenue Loss (USD)'] = display['Revenue Loss (USD)'].apply(lambda x: f"${x:,.0f}")
st.dataframe(display, use_container_width=True, hide_index=True)

# --- Transit Hub ---
st.divider()
st.subheader("🚇 Undersupplied Zones Near Transit Hubs (800m)")
st.caption("Highest priority for fleet redeployment: high foot traffic + unmet demand.")
transit_df = load_transit()
if not transit_df.empty:
    transit_df.columns = ['Transit Hub','Zone','Borough','Revenue Loss (USD)','Distance (m)']
    transit_df['Revenue Loss (USD)'] = transit_df['Revenue Loss (USD)'].apply(lambda x: f"${float(x):,.0f}")
    st.dataframe(transit_df, use_container_width=True, hide_index=True)
else:
    st.info("No undersupplied zones within 800m of transit hubs.")

st.caption("Mahardi Setyoso · NYC TLC 2023 · H3 + PostGIS + dbt + Streamlit")
