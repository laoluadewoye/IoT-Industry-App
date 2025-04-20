import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_folium import st_folium
from os import getenv
from hashlib import sha256
from requests import get, Response
from folium import Map as FoliumMap, Marker as FoliumMarker, CircleMarker as FoliumCircleMarker, Icon as FoliumIcon

# Get core database environmental variables
defaults = {
    'DB_HOST': 'mongo-db', 'DB_PORT': '27017', 'DB_USER': 'web_view',
    'DB_PASSWORD_FILE': '../secrets/web_view_password.txt', 'PROXY_HOST': 'localhost', 'PROXY_PORT': '8079'
}

DB_HOST: str = getenv('DB_HOST', defaults['DB_HOST'])
DB_PORT: str = getenv('DB_PORT', defaults['DB_PORT'])
DB_USER: str = getenv('DB_USER', defaults['DB_USER'])
DB_PASSWORD_FILE: str = getenv('DB_PASSWORD_FILE', defaults['DB_PASSWORD_FILE'])
PROXY_HOST: str = getenv('PROXY_HOST', defaults['PROXY_HOST'])
PROXY_PORT: str = getenv('PROXY_PORT', defaults['PROXY_PORT'])


@st.cache_data(max_entries=5, ttl=60)
def load_sensor_data() -> list[dict]:
    # Create password hash
    hashed_data_gen_password: str = sha256(open(DB_PASSWORD_FILE).read().encode()).hexdigest()

    # Create message content
    content: dict = {
        'username': DB_USER,
        'password': hashed_data_gen_password,
        'host': DB_HOST,
        'port': DB_PORT,
    }

    # Send a get request to the proxy server
    response: Response = get(f'http://{PROXY_HOST}:{PROXY_PORT}/web_app/sensors', params=content, timeout=10)
    return response.json()['result']


@st.fragment(run_every=10)
def create_filter_settings() -> None:
    st.title('Filter Settings')

    # Selection for which sensors to view
    st.subheader('Select Location Setting')
    all_or_selected = st.radio(
        'What locations would you like the average of?',
        ['All', 'Selected Options'],
        horizontal=True,
        key='all_or_selected'
    )

    # Select the sensors if 'selected' is selected
    st.subheader('Select Sensors to View')

    # Get data and save information to session state and sensor list
    sensor_data: list[dict] = load_sensor_data()
    st.session_state['sensor_dict']: dict = {document['sensor_name']: document['_id'] for document in sensor_data}
    sensor_list: list[str] = [document['sensor_name'] for document in sensor_data]

    # Create dropdown
    selected_sensors_disabled: bool = all_or_selected == 'Selected Options'
    selected_sensors = st.multiselect(
        'Select Sensors', sensor_list, default=sensor_list[0], key='selected_sensors',
        disabled=selected_sensors_disabled
    )

    # Select what units you wish to use
    st.subheader('Select Unit of Measurement')
    metric_or_customary = st.radio(
        'What measurement system would you like to use?',
        ['Metric', 'Customary'],
        captions=['For international use.', 'Used in North America and UK.'],
        key='metric_or_customary'
    )


@st.fragment(run_every=3)
def create_sensor_map(sensor_df: pd.DataFrame) -> st.map:
    # Create the map around the DMV
    vienna_coordinates = [38.900692, -77.270946]
    sensor_map_folium: FoliumMap = FoliumMap(vienna_coordinates, zoom_start=8)

    # Add markers for each sensor
    for index, row in sensor_df.iterrows():
        # Create the popup information
        popup_text: str = f'Sensor Name: {row["Sensor Name"]}'

        # Differentiate the marker based on what is selected
        selected: bool = (
            st.session_state['all_or_selected'] == 'All' or
            row['Sensor Name'] in st.session_state['selected_sensors']
        )

        # Add new marker to the map
        if selected:
            new_marker = FoliumMarker(
                [row['Latitude'], row['Longitude']],
                popup=popup_text,
                icon=FoliumIcon(color='red'),
            )
        else:
            new_marker = FoliumCircleMarker(
                [row['Latitude'], row['Longitude']],
                popup=popup_text,
                color='blue',
                opacity=0.1,
                fill_color='blue',
                fill_opacity=0.1,
            )
        new_marker.add_to(sensor_map_folium)

    # Create a streamlit map object with folium extension
    sensor_map_st: st.map = st_folium(sensor_map_folium, use_container_width=True, key='sensor_map')

    return sensor_map_st


def create_sensor_tab() -> None:
    st.title('Sensor Summary')

    # Get data for the table
    sensor_data = load_sensor_data()
    sensor_list = [
        [document['_id'], document['sensor_name'], document['latitude'], document['longitude']]
        for document in sensor_data
    ]

    # Create the dataframe and display the table
    st.subheader('Sensor Table')
    sensor_df = pd.DataFrame(sensor_list, columns=['Mongo ID', 'Sensor Name', 'Latitude', 'Longitude'])
    st.dataframe(sensor_df)

    # Create a map of the sensors
    st.subheader('Sensor Map')
    sensor_map: st = create_sensor_map(sensor_df)


def create_real_time_tab() -> None:
    st.write('Real Time Data')


def create_historical_tab() -> None:
    st.write('Historical Data')


# Create initial settings and title
st.set_page_config(layout='wide')
st.title('Weather Data Dashboard')

# Create a sidebar
with st.sidebar:
    create_filter_settings()

# Create tabs
sensor_tab, real_time_tab, historical_tab = st.tabs(
    ['Sensor Information', 'Real Time Information', 'Historical Information']
)

with sensor_tab:
    create_sensor_tab()

with real_time_tab:
    create_real_time_tab()

with historical_tab:
    create_historical_tab()
