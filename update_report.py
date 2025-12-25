import requests
import json
import datetime
from datetime import datetime as dt, timedelta

# --- CONFIGURATION ---
USGS_SITE = "02146409"  # Archdale Dr at Little Sugar Creek
LAT, LON = 35.109028, -80.859390
NWS_OFFICE = "GSP"  # Greenville-Spartanburg (covers Charlotte area)
NWS_GRID = (49, 68)  # Grid coordinates for Charlotte area

def get_usgs_data():
    """Fetch 24h rainfall from USGS"""
    url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={USGS_SITE}&parameterCd=00045&period=P1D"
    try:
        response = requests.get(url)
        data = response.json()
        
        if 'value' in data and 'timeSeries' in data['value']:
            time_series_list = data['value']['timeSeries']
            if len(time_series_list) > 0:
                values = time_series_list[0]['values'][0]['value']
                if len(values) > 0:
                    latest_val = float(values[-1]['value'])
                    print(f"✅ USGS rainfall: {latest_val} inches")
                    return latest_val
                    
        print("⚠️ No USGS precipitation data available")
        return 0.0
            
    except Exception as e:
        print(f"❌ Error fetching USGS data: {e}")
        return 0.0

def get_current_weather():
    """Fetch current weather from NOAA for Charlotte area"""
    url = "https://api.weather.gov/stations/KCLT/observations/latest"
    
    try:
        response = requests.get(url, headers={'User-Agent': 'SWPPP-Dashboard/1.0'})
        data = response.json()
        props = data['properties']
        
        temp_c = props['temperature']['value']
        temp_f = (temp_c * 9/5) + 32 if temp_c else None
        
        wind_speed_mps = props['windSpeed']['value']
        wind_speed_mph = wind_speed_mps * 2.237 if wind_speed_mps else 0
        
        wind_dir = props['windDirection']['value'] if props['windDirection']['value'] else 0
        
        def deg_to_cardinal(deg):
            if deg is None: return "N/A"
            dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            ix = round(deg / (360. / len(dirs)))
            return dirs[ix % len(dirs)]
        
        wind_cardinal = deg_to_cardinal(wind_dir)
        humidity = props['relativeHumidity']['value']
        
        print(f"✅ Weather: {temp_f:.1f}°F, Wind: {wind_speed_mph:.1f} mph {wind_cardinal}, Humidity: {humidity}%")
        
        return {
            'temp_f': round(temp_f, 1) if temp_f else 0,
            'temp_c': round(temp_c, 1) if temp_c else 0,
            'wind_speed_mph': round(wind_speed_mph, 1),
            'wind_direction': wind_cardinal,
            'wind_direction_deg': wind_dir,
            'humidity': round(humidity) if humidity else 0,
            'description': props.get('textDescription', 'N/A')
        }
        
    except Exception as e:
        print(f"❌ Error fetching weather data: {e}")
        return {
            'temp_f': 0, 'temp_c': 0, 'wind_speed_mph': 0,
            'wind_direction': 'N/A', 'wind_direction_deg': 0,
            'humidity': 0, 'description': 'N/A'
        }

def get_forecast():
    """Fetch 7-day forecast from NWS"""
    url = f"https://api.weather.gov/gridpoints/{NWS_OFFICE}/{NWS_GRID[0]},{NWS_GRID[1]}/forecast"
    
    try:
        response = requests.get(url, headers={'User-Agent': 'SWPPP-Dashboard/1.0'})
        data = response.json()
        
        periods = data['properties']['periods'][:14]  # Get 7 days (day + night periods)
        
        forecast = []
        for i in range(0, len(periods), 2):
            day_period = periods[i]
            night_period = periods[i+1] if i+1 < len(periods) else day_period
            
            forecast.append({
                'day': day_period['name'],
                'date': day_period['startTime'][:10],
                'high': day_period['temperature'],
                'low': night_period['temperature'],
                'precipitation_prob': day_period.get('probabilityOfPrecipitation', {}).get('value', 0),
                'wind_speed': day_period['windSpeed'],
                'wind_direction': day_period['windDirection'],
                'short_forecast': day_period['shortForecast'],
                'detailed_forecast': day_period['detailedForecast']
            })
        
        print(f"✅ Retrieved {len(forecast)} day forecast")
        return forecast
        
    except Exception as e:
        print(f"❌ Error fetching forecast: {e}")
        return []

def get_alerts():
    """Fetch active NWS alerts for the area"""
    url = f"https://api.weather.gov/alerts/active?point={LAT},{LON}"
    
    try:
        response = requests.get(url, headers={'User-Agent': 'SWPPP-Dashboard/1.0'})
        data = response.json()
        
        alerts = []
        for feature in data.get('features', []):
            props = feature['properties']
            alerts.append({
                'event': props['event'],
                'severity': props['severity'],
                'urgency': props['urgency'],
                'headline': props.get('headline', 'Weather Alert'),
                'description': props.get('description', ''),
                'instruction': props.get('instruction', ''),
                'onset': props.get('onset', ''),
                'expires': props.get('expires', '')
            })
        
        if alerts:
            print(f"⚠️ {len(alerts)} active weather alerts")
        else:
            print("✅ No active weather alerts")
            
        return alerts
        
    except Exception as e:
        print(f"❌ Error fetching alerts: {e}")
        return []

def calculate_aci_305r(temp_f, wind_mph, humidity):
    """Calculate concrete evaporation rate using ACI 305R formula"""
    try:
        temp_c = (temp_f - 32) * 5/9
        rh = humidity / 100.0
        tc = temp_c
        ta = temp_c
        v = wind_mph * 1.60934
        
        evap = 5 * ((tc + 18)**2.5 - rh * (ta + 18)**2.5) * (v + 4) * 1e-6
        evap = max(0, evap)
        return round(evap, 3)
        
    except:
        return 0.42

def generate_recommendations(weather, forecast, rain_24h, evap_rate):
    """Generate construction activity recommendations"""
    
    recommendations = {
        'concrete_pouring': {'status': 'GO', 'notes': []},
        'grading_excavation': {'status': 'GO', 'notes': []},
        'asphalt_paving': {'status': 'GO', 'notes': []},
        'painting_coating': {'status': 'GO', 'notes': []},
        'crane_ops': {'status': 'GO', 'notes': []},
        'general_safety': []
    }
    
    # Concrete Pouring Assessment
    if rain_24h > 0.25:
        recommendations['concrete_pouring']['status'] = 'STOP'
        recommendations['concrete_pouring']['notes'].append('Recent rainfall - soil too wet')
    elif evap_rate > 1.0:
        recommendations['concrete_pouring']['status'] = 'CAUTION'
        recommendations['concrete_pouring']['notes'].append(f'High evaporation ({evap_rate} kg/m²/h) - increase curing')
    elif weather['temp_f'] < 40:
        recommendations['concrete_pouring']['status'] = 'CAUTION'
        recommendations['concrete_pouring']['notes'].append('Cold weather - use heated concrete/protection')
    elif weather['temp_f'] > 90:
        recommendations['concrete_pouring']['status'] = 'CAUTION'
        recommendations['concrete_pouring']['notes'].append('Hot weather - plan for early morning pours')
    else:
        recommendations['concrete_pouring']['notes'].append('Optimal conditions for concrete work')
    
    # Check upcoming rain in forecast
    upcoming_rain = False
    for day in forecast[:3]:  # Next 3 days
        if day['precipitation_prob'] > 60:
            upcoming_rain = True
            recommendations['concrete_pouring']['notes'].append(f"Rain expected {day['day']} ({day['precipitation_prob']}%)")
    
    # Grading & Excavation
    if rain_24h > 0.5:
        recommendations['grading_excavation']['status'] = 'STOP'
        recommendations['grading_excavation']['notes'].append('Soil saturated - equipment damage risk')
    elif rain_24h > 0.25:
        recommendations['grading_excavation']['status'] = 'CAUTION'
        recommendations['grading_excavation']['notes'].append('Soil wet - limited operations only')
    else:
        recommendations['grading_excavation']['notes'].append('Ground conditions suitable')
    
    # Asphalt Paving
    if rain_24h > 0.1:
        recommendations['asphalt_paving']['status'] = 'STOP'
        recommendations['asphalt_paving']['notes'].append('Surface must be dry')
    elif weather['temp_f'] < 50:
        recommendations['asphalt_paving']['status'] = 'STOP'
        recommendations['asphalt_paving']['notes'].append('Temperature too low for asphalt')
    elif upcoming_rain:
        recommendations['asphalt_paving']['status'] = 'CAUTION'
        recommendations['asphalt_paving']['notes'].append('Rain forecasted - complete quickly')
    
    # Painting/Coating
    if weather['humidity'] > 85:
        recommendations['painting_coating']['status'] = 'STOP'
        recommendations['painting_coating']['notes'].append('Humidity too high')
    elif weather['temp_f'] < 50 or weather['temp_f'] > 90:
        recommendations['painting_coating']['status'] = 'CAUTION'
        recommendations['painting_coating']['notes'].append('Temperature outside optimal range')
    elif rain_24h > 0:
        recommendations['painting_coating']['status'] = 'CAUTION'
        recommendations['painting_coating']['notes'].append('Recent moisture - verify surface dry')
    
    # Crane Operations
    if weather['wind_speed_mph'] > 20:
        recommendations['crane_ops']['status'] = 'STOP'
        recommendations['crane_ops']['notes'].append(f'Wind speed {weather["wind_speed_mph"]} mph exceeds safe limits')
    elif weather['wind_speed_mph'] > 15:
        recommendations['crane_ops']['status'] = 'CAUTION'
        recommendations['crane_ops']['notes'].append('Monitor wind speeds closely')
    
    # General Safety Alerts
    if weather['temp_f'] > 90:
        recommendations['general_safety'].append('🌡️ Heat Advisory: Ensure hydration stations, frequent breaks')
    if weather['wind_speed_mph'] > 25:
        recommendations['general_safety'].append('💨 High Wind: Secure loose materials, caution with tall equipment')
    
    return recommendations

def find_optimal_work_windows(forecast):
    """Identify best days for different activities over next week"""
    
    windows = {
        'concrete_pouring': [],
        'grading': [],
        'painting': []
    }
    
    for day in forecast:
        # Concrete windows (dry, moderate temps)
        if day['precipitation_prob'] < 30 and 45 <= day['high'] <= 85:
            windows['concrete_pouring'].append(day['day'])
        
        # Grading windows (dry)
        if day['precipitation_prob'] < 20:
            windows['grading'].append(day['day'])
        
        # Painting windows (dry, moderate humidity assumed)
        if day['precipitation_prob'] < 20 and 50 <= day['high'] <= 85:
            windows['painting'].append(day['day'])
    
    return windows

# ===== MAIN EXECUTION =====
print("🔄 Generating Construction Operations Briefing...")
print("="*60)

rain_24h = get_usgs_data()
weather = get_current_weather()
forecast = get_forecast()
alerts = get_alerts()
evap_rate = calculate_aci_305r(weather['temp_f'], weather['wind_speed_mph'], weather['humidity'])
recommendations = generate_recommendations(weather, forecast, rain_24h, evap_rate)
work_windows = find_optimal_work_windows(forecast)

# Build comprehensive report
report_data = {
    "site_info": {
        "name": "6401 South Blvd",
        "gauge": "USGS Archdale Dr",
        "location": {"lat": LAT, "lon": LON}
    },
    "current_conditions": {
        "temperature_f": weather['temp_f'],
        "temperature_c": weather['temp_c'],
        "wind_speed_mph": weather['wind_speed_mph'],
        "win
