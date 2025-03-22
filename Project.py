import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import folium
import time
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from ydata_profiling import ProfileReport
from streamlit.components.v1 import html
from datetime import datetime

# Configure page first
st.set_page_config(
    page_title="Weather Dashboard",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        'Get Help': 'https://your-help-url.com',
        'Report a bug': "https://your-bug-report-url.com",
        'About': "# Mobile-friendly Weather Dashboard"
    }
)

# Initialize geocoder
geolocator = Nominatim(user_agent="weather_app")

# Initialize session state for coordinates
if 'lat' not in st.session_state:
    st.session_state.lat = 11.7188  # Default Salem latitude
if 'lon' not in st.session_state:
    st.session_state.lon = 78.0779  # Default Salem longitude

# Map creation function
def create_map():
    m = folium.Map(
        location=[st.session_state.lat, st.session_state.lon],
        zoom_start=12,
        control_scale=True
    )

    # Add search functionality
    folium.plugins.Geocoder(
        position="topleft",
        collapsed=True,
        add_marker=True
    ).add_to(m)

    # Add click functionality
    m.add_child(folium.LatLngPopup())

    # Add default marker
    folium.Marker(
        location=[st.session_state.lat, st.session_state.lon],
        popup=f"Selected Location<br>{st.session_state.lat:.4f}, {st.session_state.lon:.4f}"
    ).add_to(m)
    return m

# Main app layout
st.title("🌍 Interactive Weather Map")

# Create two columns
col1, col2 = st.columns([2, 1])

with col1:
    # Display the map
    map_data = st_folium(
        create_map(),
        width=800,
        height=500
    )

    # Update coordinates from map interaction
    if map_data.get("last_clicked"):
        st.session_state.lat = map_data["last_clicked"]["lat"]
        st.session_state.lon = map_data["last_clicked"]["lng"]
        st.rerun()

with col2:
    st.header("Coordinates")
    
    # Display editable coordinate inputs
    lat = st.number_input("Latitude",
                         value=st.session_state.lat,
                         format="%.4f",
                         key="lat_input")

    lon = st.number_input("Longitude",
                         value=st.session_state.lon,
                         format="%.4f",
                         key="lon_input")

    # Update map when inputs change
    if lat != st.session_state.lat or lon != st.session_state.lon:
        st.session_state.lat = lat
        st.session_state.lon = lon
        st.rerun()

st.title("🌤️ Weather Data Dashboard 🌤️")

# API Configuration
apiKey = "c4955b467b19f41bfcdb6f8ef53d837e"

# 1. Add session state tracking for API data
if 'weather_data' not in st.session_state:
    st.session_state.weather_data = None
if 'last_coords' not in st.session_state:
    st.session_state.last_coords = (None, None)

# 2. Modified API handling section
if 'lat' in st.session_state and 'lon' in st.session_state:
    current_coords = (round(st.session_state.lat, 6), 
                     round(st.session_state.lon, 6))    

if 'lat' in st.session_state and 'lon' in st.session_state:
    try:
        # Add cache-busting parameter
        timestamp = int(time.time())
        completeURL = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={apiKey}&t={time.time()}"
        response = requests.get(completeURL)

        # Force new data load even for same coordinates
        
        if "last_coords" not in st.session_state:
            st.session_state.last_coords = (None, None)
            
        if (lat, lon) != st.session_state.last_coords:
            st.cache_data.clear()
            st.session_state.last_coords = (lat, lon)
        
        if response.status_code == 200:
            data = response.json()
            df = pd.json_normalize(data)

            # Get proper location name using reverse geocoding
            try:
                location = geolocator.reverse(
                   f"{lat}, {lon}",
                   exactly_one=True,
                   language="en"
                )
                place_name = location.address.split(",")[0]  # Gets most specific name
                country = location.raw.get('address', {}).get('country', '')
            except Exception as e:
                place_name = data.get('name', 'Unknown Location')
                country = data.get('sys', {}).get('country', '') 

            # Then update the display line (CRUCIAL CHANGE):
            st.subheader(f"{place_name}, {country}")  # Changed from 'city' to 'place_name'
            
            # Convert list/dict values to strings
            df = df.applymap(lambda x: str(x) if isinstance(x, (list, dict)) else x)
            
            # Create tabs for better organization
            tab1, tab2, tab3 = st.tabs(["Current Weather", "Detailed Analysis", "Weather Forecast"])
            
            with tab1:
                # Display vertical data table
                st.subheader(f"{place_name}, {country}")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Temperature", f"{round(data['main']['temp']-273.15,1)}°C")
                    st.metric("Humidity", f"{data['main']['humidity']}%")
                with col_b:
                    st.metric("Condition", data['weather'][0]['main'])
                    st.metric("Wind Speed", f"{data['wind']['speed']} m/s")
                
                with st.expander("Show Full Data Table"):
                    vertical_df = df.T.reset_index()
                    vertical_df.columns = ['Attribute', 'Value']
                    st.dataframe(
                        vertical_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Attribute": st.column_config.Column(width="small"),
                            "Value": st.column_config.Column(width="large")
                        }
                    )

            with tab2:
                # Visualization and profiling in separate tab
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                
                if numeric_cols:
                    col = st.selectbox("Select a metric to visualize", numeric_cols)
                    
                    if len(df) == 1:
                        st.write(f"### Current {col} Value")
                        st.metric(label=col, value=df[col].iloc[0])
                    else:
                        fig = px.bar(df, x=df.index, y=col, title=f"{col} Values")
                        st.plotly_chart(fig)
                else:
                    st.warning("No numeric columns available for visualization")
                
                # Generate and display report in the analysis tab
                with st.spinner("Generating detailed analysis..."):
                    profile = ProfileReport(df, explorative=True, minimal=True)
                    st.write("Comprehensive Analysis")
                    
                    # Generate HTML report and display with fixed height
                    html_report = profile.to_html()
                    html(html_report, height=800, scrolling=True, width=1400)

            with tab3: 
                API_KEY = "c4955b467b19f41bfcdb6f8ef53d837e"
                st.title("🏙️ Smart Campus Weather Analytics")
                # 🔹 Get User Input (City & Country Code)
                city = st.text_input("📍 Enter your location (City, Country Code):", "Salem,IN")
                 
                # Initialize session state
                if 'clicked' not in st.session_state:
                   st.session_state.clicked = False
                def set_clicked():
                   st.session_state.clicked = True 

                st.button("🔍 Get Weather Analysis",on_click=set_clicked)
                if st.session_state.clicked:
                    try:
                        # 🔹 Fetch Current Weather Data
                        URL_CURRENT = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
                        current_response = requests.get(URL_CURRENT)
   
                        if current_response.status_code == 200:
                           current_weather = current_response.json()

                           # Extract current weather data
                           temperature = current_weather['main']['temp']
                           humidity = current_weather['main']['humidity']
                           rain = current_weather.get('rain', {}).get('1h', 0)  # Rainfall in mm (last hour)
                           wind_speed = current_weather.get('wind', {}).get('speed', 0)
                           current_dt = datetime.fromtimestamp(current_weather['dt'])
                           month = current_dt.month

                           # 🔹 Smart HVAC Control Function
                           def optimize_hvac(temp, humidity):
                               if temp > 32:
                                  return "Increase AC cooling"
                               elif temp < 18:
                                  return "Increase heating"
                               elif humidity > 70:
                                  return "Activate dehumidifier"
                               else:
                                  return "Maintain current settings"

                           # 🔹 Smart Irrigation Decision Function
                           def irrigation_decision(rainfall, humidity):
                               if rainfall > 5:
                                  return "No irrigation needed (Rainfall sufficient)"
                               elif humidity < 40:
                                  return "Irrigate immediately (Dry conditions detected)"
                               elif humidity < 60:
                                  return "Monitor soil moisture (Irrigation may be required soon)"
                               else:
                                  return "No irrigation needed (Humidity sufficient)"

                           # 🔹 Get recommendations
                           hvac_action = optimize_hvac(temperature, humidity)
                           irrigation_action = irrigation_decision(rain, humidity)

                           # 🔹 Display Current Weather Data
                           st.subheader("📍 Current Weather")
                           # Create three columns
                           col1, col2  = st.columns([1,3])

                           with col1:
                             st.metric(label="🌡️ Temperature", value=f"{temperature}°C")
                             st.metric(label="🌧️ Rainfall (1h)", value=f"{rain} mm")
                             st.metric(label="🌬️ Wind Speed", value=f"{wind_speed} m/s")
                           with col2:
                             st.metric(label="💧 Humidity", value=f"{humidity}%")
                             st.metric(label="⚙️ HVAC Action", value=hvac_action)
                             st.metric(label="🚜 Irrigation Action", value=irrigation_action)

                           # 🔹 Fetch 5-Day Weather Forecast
                           URL_FORECAST = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
                           forecast_response = requests.get(URL_FORECAST)

                           if forecast_response.status_code == 200:
                               forecast_data = forecast_response.json()
                               forecast_list = []

                               for entry in forecast_data["list"]:
                                   timestamp = entry["dt"]
                                   # Convert timestamp to datetime object
                                   dt_object = datetime.fromtimestamp(timestamp)
                                   # Separate date and time components
                                   date = dt_object.strftime('%Y-%m-%d')
                                   time = dt_object.strftime('%H:%M')
                                   # Properly extract weather values
                                   main_data = entry['main']
                                   temp = main_data['temp']          # Temperature
                                   humidity = main_data['humidity']  # Humidity
                                   weather_desc = entry["weather"][0]["description"]
                                   rain_forecast = entry.get("rain", {}).get("3h", 0)  # Rainfall in mm (last 3 hours)
                                   wind_speed = entry.get('wind', {}).get('speed', 0) 
                                   hvac_recommendation = optimize_hvac(temp, humidity)
                                   irrigation_recommendation = irrigation_decision(rain_forecast, humidity)

                                   forecast_list.append([date, time, temp, humidity, wind_speed, weather_desc, hvac_recommendation, irrigation_recommendation])

                               # Convert list to DataFrame for better visualization
                               df_forecast = pd.DataFrame(forecast_list, columns=["Date", "Time", "Temperature (°C)", "Humidity (%)","Wind Speed (m/s)", "Weather", "HVAC Recommendation", "Irrigation Recommendation"])

                               # Display forecast table
                               st.subheader("📅 5-Day Weather Forecast (Every 3 Hours)")
                               st.dataframe(df_forecast, use_container_width=True)
                           else:
                               st.error("⚠️ Error: Invalid location or API issue. Please try again.") 
                    except Exception as e:
                       st.error(f"⚠️ Connection Error: {str(e)}")           
        else:
            st.error(f"🌩️ API Error: {response.status_code} - {response.text}")
            
    except ValueError:
        st.warning("⚠️ Please enter valid numerical coordinates")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


# Mobile optimization
st.markdown("""
<style>
    .folium-map {
        touch-action: auto !important;
    }
    .leaflet-control-geocoder {
        font-size: 18px !important;
    }
    /* Larger input fields for mobile */
    .stNumberInput input {
        font-size: 16px !important;
        padding: 12px !important;
    }
</style>
""", unsafe_allow_html=True)