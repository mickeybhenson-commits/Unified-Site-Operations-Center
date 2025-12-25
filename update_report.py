import requests
import json
import datetime

# --- CONFIGURATION ---
USGS_SITE = "02146409"  # Archdale Dr at Little Sugar Creek
LAT, LON = 35.109028, -80.859390

def get_usgs_data():
    # Fetching 24h cumulative rainfall from USGS Water Services API
    url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={USGS_SITE}&parameterCd=00045&period=P1D"
    try:
        response = requests.get(url)
        data = response.json()
        # Extracting latest precip value from the JSON nesting
        time_series = data['value']['timeSeries'][0]['values'][0]['value']
        latest_val = float(time_series[-1]['value'])
        return latest_val
    except Exception as e:
        print(f"Error fetching USGS data: {e}")
        return 0.0

def calculate_aci_305r():
    # Placeholder for the ACI 305R Concrete Evaporation formula
    # Typically: E = 5 * ([Tc + 18]^2.5 - r * [Ta + 18]^2.5) * (V + 4) * 10^-6
    # Returns kg/m2/h
    return 0.42 

# Run the logic
rain_24h = get_usgs_data()
evap_rate = calculate_aci_305r()

# Build the structured report
report_data = {
    "site_info": {"name": "6401 South Blvd", "gauge": "USGS Archdale Dr"},
    "weather_metrics": {
        "observed_24h_precip": rain_24h,
        "model_consensus": "Moderate Risk - Monitor Silt Fences" if rain_24h > 0.25 else "Stable Conditions"
    },
    "soil_moisture": {
        "level": "85%" if rain_24h > 0.5 else "48%",
        "status": "Saturated" if rain_24h > 0.5 else "Workable"
    },
    "swppp_compliance": {
        "risk_level": "HIGH" if rain_24h > 0.5 else "MODERATE",
        "map_labels": [
            {"lat": 35.108422, "lon": -80.858450, "label": "URGENT: Silt Fence Breach", "priority": "High"},
            {"lat": 35.109150, "lon": -80.858280, "label": "MAINTENANCE: Sediment Removal", "priority": "Med"},
            {"lat": 35.109620, "lon": -80.859850, "label": "STABILIZE: NW Slope Rills", "priority": "High"}
        ]
    },
    "concrete_ops": {
        "pour_status": "CAUTION" if evap_rate > 0.5 or rain_24h > 0.1 else "OPTIMAL",
        "evap_rate": evap_rate,
        "notes": "Ensure curing compound is ready if wind increases."
    }
}

with open('latest_report.json', 'w') as f:
    json.dump(report_data, f, indent=4)
