import streamlit as st
import pandas as pd
import pydeck as pdk
import json
from datetime import datetime

# --- CONFIG ---
MAPBOX_TOKEN = st.secrets["MAPBOX_TOKEN"]
st.set_page_config(
    layout="wide",
    page_title="Construction Operations Daily Briefing",
    page_icon="🏗️"
)

# Load data
try:
    with open('latest_report.json') as f:
        data = json.load(f)
except:
    st.error("❌ No data found. Please trigger the GitHub Action.")
    st.stop()

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .big-font { font-size: 2rem !important; font-weight: bold; }
    .status-go { color: #00ff00; }
    .status-caution { color: #ffaa00; }
    .status-stop { color: #ff0000; }
    .alert-box { padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0; }
    .alert-severe { background-color: #ff000020; border-left: 4px solid #ff0000; }
    .alert-moderate { background-color: #ffaa0020; border-left: 4px solid #ffaa00; }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.title("🏗️ Construction Operations Daily Briefing")
st.subheader(f"📍 {data['site_info']['name']}")

try:
    last_update = datetime.fromisoformat(data['last_updated'])
    st.caption(f"🕒 Generated: {last_update.strftime('%A, %B %d, %Y at %I:%M %p')}")
except:
    st.caption("🕒 Last Updated: Recently")

st.divider()

# --- ACTIVE ALERTS SECTION ---
if data.get('active_alerts') and len(data['active_alerts']) > 0:
    st.markdown("## ⚠️ ACTIVE WEATHER ALERTS")
    for alert in data['active_alerts']:
        severity_class = "alert-severe" if alert['severity'] in ['Severe', 'Extreme'] else "alert-moderate"
        st.markdown(f"""
        <div class="alert-box {severity_class}">
            <strong>{alert['event']}</strong> - {alert['severity']}<br/>
            {alert['headline']}<br/>
            <small>{alert.get('instruction', '')}</small>
        </div>
        """, unsafe_allow_html=True)
    st.divider()

# --- CURRENT CONDITIONS ---
st.markdown("## 🌤️ Current Conditions")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Temperature", f"{data['current_conditions']['temperature_f']}°F")

with col2:
    st.metric("Wind", f"{data['current_conditions']['wind_speed_mph']} mph", 
              data['current_conditions']['wind_direction'])

with col3:
    st.metric("Humidity", f"{data['current_conditions']['humidity_percent']}%")

with col4:
    st.metric("24hr Rainfall", f"{data['current_conditions']['precipitation_24h']} in")

with col5:
    st.metric("Soil Status", data['soil_moisture']['status'])

st.divider()

# --- ACTIVITY RECOMMENDATIONS ---
st.markdown("## 📋 Today's Activity Recommendations")

recs = data['activity_recommendations']

col1, col2, col3 = st.columns(3)

def display_activity(col, title, icon, activity_data):
    with col:
        status = activity_data['status']
        
        if status == 'GO':
            col.success(f"{icon} **{title}**")
            status_class = "status-go"
        elif status == 'CAUTION':
            col.warning(f"{icon} **{title}**")
            status_class = "status-caution"
        else:
            col.error(f"{icon} **{title}**")
            status_class = "status-stop"
        
        col.markdown(f"<div class='big-font {status_class}'>{status}</div>", unsafe_allow_html=True)
        
        for note in activity_data['notes']:
            col.write(f"• {note}")

display_activity(col1, "Concrete Pouring", "🧱", recs['concrete_pouring'])
display_activity(col2, "Grading/Excavation", "🚜", recs['grading_excavation'])
display_activity(col3, "Crane Operations", "🏗️", recs['crane_ops'])

st.divider()

col1, col2 = st.columns(2)
display_activity(col1, "Asphalt Paving", "🛣️", recs['asphalt_paving'])
display_activity(col2, "Painting/Coating", "🎨", recs['painting_coating'])

# General Safety
if recs['general_safety']:
    st.warning("**⚠️ Safety Alerts:**")
    for alert in recs['general_safety']:
        st.write(f"• {alert}")

st.divider()

# --- 7-DAY FORECAST ---
st.markdown("## 📅 7-Day Forecast & Planning")

if data.get('forecast_7day'):
    forecast_df = pd.DataFrame(data['forecast_7day'])
    
    # Create forecast table
    display_df = forecast_df[['day', 'high', 'low', 'precipitation_prob', 'wind_speed', 'short_forecast']].copy()
    display_df.columns = ['Day', 'High °F', 'Low °F', 'Rain %', 'Wind', 'Conditions']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Detailed forecast expander
    with st.expander("📖 Detailed Forecast"):
        for day in data['forecast_7day']:
            st.markdown(f"**{day['day']}** - {day['date']}")
            st.write(day['detailed_forecast'])
            st.divider()

st.divider()

# --- OPTIMAL WORK WINDOWS ---
st.markdown("## 🎯 Optimal Work Windows (Next 7 Days)")

windows = data.get('optimal_work_windows', {})

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🧱 Concrete Pouring")
    if windows.get('concrete_pouring'):
        for day in windows['concrete_pouring']:
            st.success(f"✅ {day}")
    else:
        st.warning("⚠️ No optimal days forecasted")

with col2:
    st.markdown("### 🚜 Grading Operations")
    if windows.get('grading'):
        for day in windows['grading']:
            st.success(f"✅ {day}")
    else:
        st.warning("⚠️ No optimal days forecasted")

with col3:
    st.markdown("### 🎨 Painting/Coating")
    if windows.get('painting'):
        for day in windows['painting']:
            st.success(f"✅ {day}")
    else:
        st.warning("⚠️ No optimal days forecasted")

st.divider()

# --- SWPPP MAP ---
st.markdown("## 📍 SWPPP Compliance & Field Maintenance Map")
st.caption("Satellite view with active inspection points")

df = pd.DataFrame(data['swppp_compliance']['map_labels'])

if 'color' not in df.columns:
    df['color'] = df['priority'].apply(lambda x: [230, 0, 0] if x == 'High' else [255, 165, 0])

view_state = pdk.ViewState(
    latitude=data['site_info']['location']['lat'],
    longitude=data['site_info']['location']['lon'],
    zoom=17.5,
    pitch=45
)

points = pdk.Layer(
    "ScatterplotLayer",
    df,
    get_position="[lon, lat]",
    get_color="color",
    get_radius=8,
    pickable=True
)

labels = pdk.Layer(
    "TextLayer",
    df,
    get_position="[lon, lat]",
    get_text="label",
    get_size=16,
    get_color=[255, 255, 255],
    get_alignment_baseline="'bottom'",
    get_pixel_offset=[0, -15],
)

deck = pdk.Deck(
    map_style="mapbox://styles/mapbox/satellite-v9",
    api_keys={"mapbox": MAPBOX_TOKEN},
    initial_view_state=view_state,
    layers=[points, labels],
    tooltip={"text": "{label}\nPriority: {priority}"}
)

st.pydeck_chart(deck)

with st.expander("📋 Inspection Points Details"):
    st.dataframe(
        df[['label', 'priority', 'lat', 'lon']],
        use_container_width=True,
        hide_index=True
    )

st.divider()

# --- FOOTER ---
st.caption(f"📡 Data Sources: {data['site_info']['gauge']} | NOAA NWS | KCLT Weather Station")
st.caption("🔄 Auto-updates daily at 8:30 AM EST | Manual: GitHub Actions → Run Workflow")
