import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from os import getenv
from hashlib import sha256
from requests import get, Response
from folium import Map as FoliumMap, Marker as FoliumMarker, CircleMarker as FoliumCircleMarker, Icon as FoliumIcon
from typing import Union

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


def load_data(content: dict[str, str]) -> Union[dict[str, list], list[dict]]:
    # Send a get request to the proxy server
    response: Response = get(f'http://{PROXY_HOST}:{PROXY_PORT}/web_app', json=content, timeout=10)

    # Get json result
    response_json = response.json()
    if response_json['status'] != 'Success':
        st.error(response_json['message'])

    return response.json()['result']


@st.cache_data(max_entries=3, ttl=10)
def load_sensor_data() -> list[dict]:
    # Create password hash
    hashed_data_gen_password: str = sha256(open(DB_PASSWORD_FILE).read().encode()).hexdigest()

    # Create message content
    content: dict = {
        'purpose': 0,
        'username': DB_USER,
        'password': hashed_data_gen_password,
        'host': DB_HOST,
        'port': DB_PORT
    }

    return load_data(content)


def load_real_time_data() -> dict[str, list]:
    # Create password hash
    hashed_data_gen_password: str = sha256(open(DB_PASSWORD_FILE).read().encode()).hexdigest()

    # Obtain filters with default handling
    all_or_selected_filter = st.session_state.get('all_or_selected', 'Empty')
    selected_sensors_filter = st.session_state.get('selected_sensors', ['Empty'])
    metric_or_customary_filter = st.session_state.get('metric_or_customary', 'Empty')

    # Create message content
    content: dict = {
        'purpose': 1,
        'username': DB_USER,
        'password': hashed_data_gen_password,
        'host': DB_HOST,
        'port': DB_PORT,
        'filters': {
            'metric_or_customary': metric_or_customary_filter,
            'all_or_selected': all_or_selected_filter,
            'selected_sensors': selected_sensors_filter
        }
    }

    return load_data(content)


@st.fragment
def create_filter_settings() -> None:
    st.title('Filter Settings')
    st.text('Use this sidebar to choose what sensors you wish to examine.')

    # Select what measurement system you wish to use
    st.subheader('Select Measurement System')
    metric_or_customary = st.radio(
        'What measurement system would you like to use?',
        ['Metric', 'Customary'],
        captions=['For international use.', 'Used in North America and UK.'],
        key='metric_or_customary'
    )

    if metric_or_customary == 'Metric':
        st.session_state['unit_modifiers'] = {
            'Humidity': '%', 'Precipitation': 'mm', 'Pressure': 'mb', 'Temperature': '°C', 'UV Index': 'uvi',
            'Wind Degree': '°', 'Wind Speed': 'kph'
        }
    else:
        st.session_state['unit_modifiers'] = {
            'Humidity': '%', 'Precipitation': 'in', 'Pressure': 'inHg', 'Temperature': '°F', 'UV Index': 'uvi',
            'Wind Degree': '°', 'Wind Speed': 'mph'
        }

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
    if all_or_selected == 'All':
        st.text('To use this feature, select "Selected Options" above.')

    # Get data and save information to session state and sensor list
    sensor_data: list[dict] = load_sensor_data()
    sensor_list: list[str] = [document['sensor_name'] for document in sensor_data]

    # Create dropdown
    selected_sensors_disabled: bool = all_or_selected == 'All'
    selected_sensors = st.multiselect(
        'Select Sensors', sensor_list, default=sensor_list[0], disabled=selected_sensors_disabled,
        key='selected_sensors',
    )


@st.fragment(run_every=3)
def create_sensor_map() -> st.map:
    # Create the map around the DMV
    vienna_coordinates = [38.900692, -77.270946]
    sensor_map_folium: FoliumMap = FoliumMap(vienna_coordinates, zoom_start=8)

    # Add markers for each sensor
    for index, row in st.session_state['sensor_df'].iterrows():
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
    st.text('This tab provides a summary of the sensors in the database, along with their locations in Maryland.')

    # Get data for the table
    sensor_data = load_sensor_data()
    sensor_list = [
        [
            document['_id'], document['sensor_name'], document['city'], document['county'], document['state'],
            document['latitude'], document['longitude']
        ]
        for document in sensor_data
    ]

    # Create the dataframe and display the table
    st.subheader('Sensor Table')
    st.text('This table provides a summary of the sensors in the database, along with their locations in Maryland.')
    st.session_state['sensor_df']: pd.DataFrame = pd.DataFrame(sensor_list, columns=[
        'Mongo ID', 'Sensor Name', 'City', 'County', 'State', 'Latitude', 'Longitude'
    ])
    st.dataframe(st.session_state['sensor_df'])

    # Create a map of the sensors
    st.subheader('Sensor Map')
    st.text('This map provides a summary of the sensors in the database, along with their locations in Maryland.')
    st.text('Red markers represent sensors that are selected, while faint blue markers represent sensors that are not.')
    sensor_map: st = create_sensor_map()


@st.fragment(run_every=3)
def create_real_time_data_containers(metric_package) -> None:
    # Create container

    for metric_key, metric_name, metric_modifier in metric_package:
        ...


def create_real_time_tab() -> None:
    st.title('Latest Real Time Analytics')
    st.text('This section provides real time summaries for the selected weather sensors in the database.')

    # Get data for boxes
    real_time_data: dict[str, list] = load_real_time_data()
    st.write(real_time_data)

    # Create metrics
    metric_keys = list(real_time_data.keys())
    generic_metric_names = [
        'Humidity', 'Precipitation', 'Pressure', 'Temperature', 'UV Index', 'Wind Degrees', 'Wind Direction',
        'Wind Speed'
    ]
    metric_modifiers = list(st.session_state['unit_modifiers'].values())
    create_real_time_data_containers(zip(metric_keys, generic_metric_names, metric_modifiers))


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
