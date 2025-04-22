import streamlit as st
from WebAppComponents import (pass_data_updates, create_filter_settings, create_sensor_tab, create_real_time_tab,
                              create_historical_tab, create_anomaly_tab)

# Create initial settings and title
st.set_page_config(layout='wide')
st.title('Weather Data Dashboard')

# Create a section to pass data updates
pass_data_updates()

# Create a sidebar
with st.sidebar:
    create_filter_settings()

# Create tabs
sensor_tab, real_time_tab, historical_tab, anomaly_tab = st.tabs(
    ['Sensor Information', 'Real Time Information', 'Historical Information', 'Anomaly Information']
)

with sensor_tab:
    create_sensor_tab()

with real_time_tab:
    create_real_time_tab()

with historical_tab:
    create_historical_tab()

with anomaly_tab:
    create_anomaly_tab()
