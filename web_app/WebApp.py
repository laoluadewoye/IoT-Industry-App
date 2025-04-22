import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from os import getenv
from hashlib import sha256
from requests import get, Response
from folium import (Map as FoliumMap, Marker as FoliumMarker, CircleMarker as FoliumCircleMarker, Icon as FoliumIcon,
                    FeatureGroup as FoliumFeatureGroup)
from typing import Union
from collections import Counter
from datetime import datetime, timedelta
from threading import Thread, Event
from time import sleep

# Get core database environmental variables
defaults: dict[str, str] = {
    'DB_HOST': 'mongo-db', 'DB_PORT': '27017', 'DB_USER': 'web_view',
    'DB_PASSWORD_FILE': '../secrets/web_view_password.txt', 'PROXY_HOST': 'localhost', 'PROXY_PORT': '8079'
}

DB_HOST: str = getenv('DB_HOST', defaults['DB_HOST'])
DB_PORT: str = getenv('DB_PORT', defaults['DB_PORT'])
DB_USER: str = getenv('DB_USER', defaults['DB_USER'])
DB_PASSWORD_FILE: str = getenv('DB_PASSWORD_FILE', defaults['DB_PASSWORD_FILE'])
PROXY_HOST: str = getenv('PROXY_HOST', defaults['PROXY_HOST'])
PROXY_PORT: str = getenv('PROXY_PORT', defaults['PROXY_PORT'])

# Create objects for storing database data
SENSOR_DATA: Union[list[dict], None] = None
REAL_TIME_DATA: Union[dict[str, list], None] = None
HISTORICAL_DATA: Union[dict[str, list], None] = None

# Reload speed
FRAGMENT_RERUN_SPEED: int = 5
DATA_UPDATE_SPEED: int = 3


def load_data(content: dict[str, str]) -> Union[dict[str, list], list[dict], None]:
    # Send a get request to the proxy server
    response: Response = get(f'http://{PROXY_HOST}:{PROXY_PORT}/web_app', json=content, timeout=10)

    # Get json result
    response_json = response.json()
    if response_json['status'] != 'Success':
        st.error(response_json['message'])
        return None

    return response.json()['result']


def load_sensor_data() -> Union[list[dict], None]:
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


def load_real_time_data() -> Union[dict[str, list], None]:
    # Create password hash
    hashed_data_gen_password: str = sha256(open(DB_PASSWORD_FILE).read().encode()).hexdigest()

    # Obtain filters with default handling
    all_or_selected_filter: str = st.session_state.get('all_or_selected', 'Empty')
    selected_sensors_filter: str = st.session_state.get('selected_sensors', ['Empty'])
    metric_or_customary_filter: str = st.session_state.get('metric_or_customary', 'Empty')

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


def load_historical_data() -> Union[dict[str, list], None]:
    # Create password hash
    hashed_data_gen_password: str = sha256(open(DB_PASSWORD_FILE).read().encode()).hexdigest()

    # Obtain filters with default handling
    all_or_selected_filter: str = st.session_state.get('all_or_selected', 'Empty')
    selected_sensors_filter: str = st.session_state.get('selected_sensors', ['Empty'])
    metric_or_customary_filter: str = st.session_state.get('metric_or_customary', 'Empty')

    # Obtain time range with default handling (5 minute default)
    end_date_time_filter: Union[datetime, str] = st.session_state.get('end_date_time', datetime.now())
    start_date_time_filter: Union[datetime, str] = st.session_state.get(
        'start_date_time', end_date_time_filter - timedelta(minutes=5)
    )

    end_date_time_filter = end_date_time_filter.strftime('%Y-%m-%d %H:%M:%S')
    start_date_time_filter = start_date_time_filter.strftime('%Y-%m-%d %H:%M:%S')

    # Create message content
    content: dict = {
        'purpose': 2,
        'username': DB_USER,
        'password': hashed_data_gen_password,
        'host': DB_HOST,
        'port': DB_PORT,
        'filters': {
            'metric_or_customary': metric_or_customary_filter,
            'all_or_selected': all_or_selected_filter,
            'selected_sensors': selected_sensors_filter
        },
        'time_range': {
            'start_date_time': start_date_time_filter,
            'end_date_time': end_date_time_filter
        }
    }

    return load_data(content)


def create_time_filter_settings() -> None:
    st.subheader('Select Time Range')
    st.text('This feature is for viewing historical data and anomaly alerts.')

    # Create choices
    date_time_range_choice = st.radio(
        "Select the range of data you want to view:",
        [
            'Last 5 Minutes', 'Last Half Hour', 'Last Hour', 'Last 5 Hours',
            'Last Day', 'Last Week', 'Last Month', 'Custom Range'
        ],
        horizontal=True,
        key="date_time_range_choice"
    )
    custom_time_disabled: bool = date_time_range_choice != 'Custom Range'

    # Create inputs for a custom time range
    st.subheader('Select Time Range: Start Information')
    st.text('To use this feature, select "Custom Range" above.')
    custom_start_date = st.date_input(
        'Select Start Date:', 'today', disabled=custom_time_disabled, key='custom_start_date'
    )
    custom_start_time = st.time_input(
        'Select Start Time:', '00:00', disabled=custom_time_disabled, key='custom_start_time'
    )

    st.subheader('Select Time Range: End Information')
    st.text('To use this feature, select "Custom Range" above.')
    custom_end_date = st.date_input('Select End Date:', 'today', disabled=custom_time_disabled, key='custom_end_date')
    custom_end_time = st.time_input('Select End Time:', '23:59', disabled=custom_time_disabled, key='custom_end_time')

    # Calculate the start and end dates and times
    end_date_time = datetime.now()
    if date_time_range_choice != 'Custom Range':
        default_deltas = {
            'Last 5 Minutes': timedelta(minutes=5),
            'Last Half Hour': timedelta(hours=0.5),
            'Last Hour': timedelta(hours=1),
            'Last 5 Hours': timedelta(hours=5),
            'Last Day': timedelta(days=1),
            'Last Week': timedelta(days=7),
            'Last Month': timedelta(days=30)
        }
        st.session_state['start_date_time'] = end_date_time - default_deltas[date_time_range_choice]
        st.session_state['end_date_time'] = end_date_time
    else:
        st.session_state['start_date_time'] = datetime.combine(custom_start_date, custom_start_time)
        st.session_state['end_date_time'] = datetime.combine(custom_end_date, custom_end_time)


@st.fragment(run_every=FRAGMENT_RERUN_SPEED)
def create_filter_settings() -> None:
    st.title('Filter Settings')
    st.text('Use this sidebar to choose what sensors you wish to examine.')
    st.text('Scroll down to view additional settings such as time ranges.')

    # Select what measurement system you wish to use
    st.subheader('Select Measurement System')
    metric_or_customary = st.radio(
        'What measurement system would you like to use?',
        ['Metric', 'Customary'],
        captions=['For international use.', 'Used in North America and UK.'],
        key='metric_or_customary'
    )

    if metric_or_customary == 'Metric':
        st.session_state['unit_modifiers'] = ['%', 'mm', 'mb', '°C', 'uvi', '°', '', 'kph']
    else:
        st.session_state['unit_modifiers'] = ['%', 'in', 'inHg', '°F', 'uvi', '°', '', 'mph']

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
    st.text('To use this feature, select "Selected Options" above.')

    # Get data and save information to session state and sensor list
    sensor_data: Union[list[dict], None] = st.session_state.get('SENSOR_DATA', None)
    if sensor_data is not None:
        sensor_list: list[str] = [document['sensor_name'] for document in sensor_data]

        # Create dropdown
        selected_sensors_disabled: bool = all_or_selected == 'All'
        selected_sensors = st.multiselect(
            'Select Sensors', sensor_list, default=sensor_list[0], disabled=selected_sensors_disabled,
            key='selected_sensors',
        )
    else:
        st.info('Sensor Data is still loading.', icon="⏳")

    # Create time filter settings
    create_time_filter_settings()


@st.fragment(run_every=FRAGMENT_RERUN_SPEED)
def create_sensor_table() -> None:
    # Get data for the table
    sensor_data: Union[list[dict], None] = st.session_state.get('SENSOR_DATA', None)
    if sensor_data is None:
        st.info('Sensor Data is still loading.', icon="⏳")
        return

    # Parse the data into a dataframe-friendly format
    sensor_list: list[list] = [
        [
            document['_id'], document['sensor_name'], document['city'], document['county'], document['state'],
            document['latitude'], document['longitude']
        ]
        for document in sensor_data
    ]

    # Create the dataframe and display the table
    st.session_state['sensor_df']: pd.DataFrame = pd.DataFrame(sensor_list, columns=[
        'Mongo ID', 'Sensor Name', 'City', 'County', 'State', 'Latitude', 'Longitude'
    ])
    st.dataframe(st.session_state['sensor_df'])


@st.fragment(run_every=FRAGMENT_RERUN_SPEED)
def create_sensor_map() -> None:
    # Early return if sensor_df doesn't exist
    if 'sensor_df' not in st.session_state:
        return

    # Add new markers to the feature group
    for index, row in st.session_state['sensor_df'].iterrows():
        # Check if it is in the feature dictionary and skip if it is
        is_red_marker = row['Sensor Name'] in st.session_state['sensor_feature_dict']['Red'].keys()
        is_blue_marker = row['Sensor Name'] in st.session_state['sensor_feature_dict']['Blue'].keys()

        # Differentiate the marker based on what is selected
        selected: bool = (
            st.session_state['all_or_selected'] == 'All' or
            row['Sensor Name'] in st.session_state['selected_sensors']
        )

        # Marker management + Skipping Logic
        if (is_red_marker and selected) or (is_blue_marker and not selected):
            continue
        elif is_red_marker and not selected:  # Move non-selected markers to blue
            st.session_state['sensor_feature_dict']['Red'].pop(row['Sensor Name'])
        elif is_blue_marker and selected:  # Move selected markers to red
            st.session_state['sensor_feature_dict']['Blue'].pop(row['Sensor Name'])

        # Create the popup information
        popup_text: str = f'Sensor Name: {row["Sensor Name"]}'

        # Create a new marker and add it to the feature dictionary
        if selected:
            new_marker: Union[FoliumMarker, FoliumCircleMarker] = FoliumMarker(
                [row['Latitude'], row['Longitude']],
                popup=popup_text,
                icon=FoliumIcon(color='red'),
            )
            st.session_state['sensor_feature_dict']['Red'][row['Sensor Name']] = new_marker
        else:
            new_marker: Union[FoliumMarker, FoliumCircleMarker] = FoliumCircleMarker(
                [row['Latitude'], row['Longitude']],
                popup=popup_text,
                color='blue',
                opacity=0.1,
                fill_color='blue',
                fill_opacity=0.1,
            )
            st.session_state['sensor_feature_dict']['Blue'][row['Sensor Name']] = new_marker

    # Establish a new map
    vienna_coordinates: list[float] = [38.900692, -77.270946]  # Create the map around the DMV
    zoom_level = 8
    sensor_map = FoliumMap(vienna_coordinates, zoom_start=zoom_level)

    # Create new feature group and populate it
    sensor_feature_group: FoliumFeatureGroup = FoliumFeatureGroup(name='Sensors')
    for marker in st.session_state['sensor_feature_dict']['Blue'].values():
        sensor_feature_group.add_child(marker)
    for marker in st.session_state['sensor_feature_dict']['Red'].values():
        sensor_feature_group.add_child(marker)

    # Create a streamlit map object with folium extension
    sensor_map_st: st.map = st_folium(
        sensor_map,
        feature_group_to_add=sensor_feature_group,
        use_container_width=True,
        key='sensor_map'
    )


def create_sensor_tab() -> None:
    st.title('Sensor Summary')
    st.text('This tab provides a summary of the sensors in the database, along with their locations in Maryland.')

    # Create the sensor table
    st.subheader('Sensor Table')
    st.text('This table provides a summary of the sensors in the database, along with their locations in Maryland.')
    create_sensor_table()

    # Create a map of the sensors
    st.subheader('Sensor Map')
    st.text('This map provides a summary of the sensors in the database, along with their locations in Maryland.')
    st.text('Red markers represent sensors that are selected, while faint blue markers represent sensors that are not.')

    # Create a persistent feature group dictionary
    if 'sensor_feature_dict' not in st.session_state:
        st.session_state['sensor_feature_dict']: dict[str, Union[FoliumMarker, FoliumCircleMarker]] = {}
        st.session_state['sensor_feature_dict']['Red'] = {}
        st.session_state['sensor_feature_dict']['Blue'] = {}

    # Add markers to the map
    create_sensor_map()


def create_real_time_data_container(real_time_data: dict[str, list], metric_package: zip) -> None:
    # Create container
    with st.container(border=True, key='real_time_data_container'):
        # Create columns to place information in
        col1, col2, col3 = st.columns(3, gap='medium')
        col4, col5, col6 = st.columns(3, gap='medium')
        _, col7, _ = st.columns(3, gap='medium')

        # Loop through all the metrics
        columns: list = [col1, col2, col3, col4, col5, col6, col7]
        column_index: int = 0
        for metric_key, metric_name, metric_modifier in metric_package:
            if metric_name == 'Wind Direction':
                continue
            elif metric_name == 'Wind Degrees':
                # Summarize the data
                metric_data: list[dict] = real_time_data[metric_key]
                metric_total: float = sum(document['latest_value'] for document in metric_data)
                metric_avg: float = round(metric_total / len(metric_data), 2)

                # Create delta
                delta_data: list[dict] = real_time_data['wind_dir']
                delta_total: list[str] = [document['latest_value'] for document in delta_data]
                delta_mode: str = Counter(delta_total).most_common(1)[0][0]

                # Create metric
                columns[column_index].metric(metric_name, f'{metric_avg}{metric_modifier}', delta_mode)
            else:
                # Summarize the data
                metric_data: list[dict] = real_time_data[metric_key]
                metric_total: float = sum(document['latest_value'] for document in metric_data)
                metric_avg: float = round(metric_total / len(metric_data), 2)

                # Create metric
                columns[column_index].metric(metric_name, f'{metric_avg}{metric_modifier}')

            # Move to next column object
            column_index += 1


@st.fragment(run_every=FRAGMENT_RERUN_SPEED)
def create_real_time_tab() -> None:
    st.title('Latest Real Time Analytics')
    st.text('This section provides real time summaries for the selected weather sensors in the database.')

    # Create a header for the real time data
    if st.session_state['all_or_selected'] == 'All':
        st.header('The Latest Real-Time Data for All Sensors')
    else:
        st.header('The Latest Real-Time Data for Selected Sensors')

        # Create additional text
        selected_sensor_cities: list[str] = st.session_state['sensor_df'][
            st.session_state['sensor_df']['Sensor Name'].isin(st.session_state['selected_sensors'])
        ]['City'].to_list()
        if len(selected_sensor_cities) > 3:
            cities_str: str = ', '.join(selected_sensor_cities[:3])
            st.text(f'The averages are calculated from {cities_str}, '
                    f'and {len(selected_sensor_cities) - 3} other locations.')
        else:
            cities_str: str = ', '.join(selected_sensor_cities)
            st.text(f'The averages are calculated from {cities_str[:-2]}.')

    # Get data for boxes
    real_time_data: Union[dict[str, list], None] = st.session_state.get('REAL_TIME_DATA', None)
    if real_time_data is not None:
        # Create metrics
        metric_keys: list[str] = list(real_time_data.keys())
        generic_metric_names: list[str] = [
            'Humidity', 'Precipitation', 'Air Pressure', 'Temperature', 'UV Index', 'Wind Degrees', 'Wind Direction',
            'Wind Speed'
        ]
        metric_modifiers: list[str] = list(st.session_state['unit_modifiers'])
        create_real_time_data_container(real_time_data, zip(metric_keys, generic_metric_names, metric_modifiers))
    else:
        st.info('Real Time Data is still loading.', icon="⏳")


def create_time_charts(historical_data: dict[str, list], metric_package: zip) -> None:
    for metric_key, metric_name, metric_modifier in metric_package:
        # Create time-zone aware dates
        start_date_str: Union[datetime, str] = st.session_state['start_date_time'] - timedelta(hours=4)
        end_date_str: Union[datetime, str] = st.session_state['end_date_time'] - timedelta(hours=4)

        start_date_str = start_date_str.strftime("%d %b %Y, %I:%M%p")
        end_date_str = end_date_str.strftime("%d %b %Y, %I:%M%p")

        st.subheader(f'Historical {metric_name} Data from {start_date_str} to {end_date_str}.')

        # Create dataframe
        historical_df: pd.DataFrame = pd.DataFrame(historical_data[metric_key])
        historical_df['time_recorded'] = pd.to_datetime(historical_df['time_recorded'], utc=True)
        historical_df['time_recorded_est'] = historical_df['time_recorded'].dt.tz_convert('US/Eastern')
        sensor_names: list = historical_df['sensor_name'].unique().tolist()

        if metric_name == 'Wind Direction':
            # Create grouping table
            historical_df_groups = historical_df.groupby(['time_recorded', 'metric'])
            historical_df_size = historical_df_groups.size().unstack(fill_value=0)

            # Create area chart
            st.area_chart(historical_df_size, stack=True, x_label='Date & Time', y_label=f'Wind Direction')
        else:
            # Create pivot table
            if len(sensor_names) > 25:
                historical_df_grouped = historical_df.groupby(['county', 'time_recorded_est'])
                historical_df_avg = historical_df_grouped['metric'].mean().reset_index()
                historical_df_pivot = historical_df_avg.pivot(
                    index='time_recorded_est', columns='county', values='metric'
                )
            else:
                historical_df_pivot = historical_df.pivot(
                    index='time_recorded_est', columns='sensor_name', values='metric'
                )

            # Create line chart
            st.line_chart(historical_df_pivot, x_label='Date & Time', y_label=f'{metric_name} ({metric_modifier})')


@st.fragment(run_every=FRAGMENT_RERUN_SPEED)
def create_historical_tab() -> None:
    st.title('Historical Weather Data')
    st.text('This section provides time-based charts showing the evolution of weather statistics.')

    # Create a description of the focused sensors for the historical data
    if st.session_state['all_or_selected'] == 'All':
        sensor_desc: str = 'All Sensors.'
    else:
        selected_sensor_cities: list[str] = st.session_state['sensor_df'][
            st.session_state['sensor_df']['Sensor Name'].isin(st.session_state['selected_sensors'])
        ]['City'].to_list()

        if len(selected_sensor_cities) > 3:
            cities_str: str = ', '.join(selected_sensor_cities[:3])
            sensor_desc: str = f'{cities_str}, and {len(selected_sensor_cities) - 3} other locations.'
        else:
            cities_str: str = ', '.join(selected_sensor_cities)
            sensor_desc: str = f'{cities_str[:-2]}.'

    st.subheader(f'The following charts display information from {sensor_desc}')

    # Get the historical data
    historical_data: Union[dict[str, list], None] = st.session_state.get('HISTORICAL_DATA', None)
    if historical_data is not None:
        # Create metrics
        metric_keys: list[str] = list(historical_data.keys())
        generic_metric_names: list[str] = [
            'Humidity', 'Precipitation', 'Air Pressure', 'Temperature', 'UV Index', 'Wind Degrees', 'Wind Direction',
            'Wind Speed'
        ]
        metric_modifiers: list[str] = list(st.session_state['unit_modifiers'])
        create_time_charts(historical_data, zip(metric_keys, generic_metric_names, metric_modifiers))
    else:
        st.info('Historical Data is still loading.', icon="⏳")


def create_anomaly_setting_widget(title: str, generic: bool, **kwargs) -> None:
    with st.popover(title):
        if generic:
            # Get parameters
            generic_unit: str = kwargs['generic_unit']
            generic_min: Union[int, float] = kwargs['generic_min']
            generic_max: Union[int, float] = kwargs['generic_max']
            generic_key: str = kwargs['generic_key']

            # Create widget
            temp_col1, temp_col2 = st.columns(2)
            with temp_col1:
                min_unit_generic = st.number_input(f'Min {generic_unit}', value=generic_min, key=f'min_{generic_key}')
            with temp_col2:
                max_unit_generic = st.number_input(f'Max {generic_unit}', value=generic_max, key=f'max_{generic_key}')
        else:
            # Get parameters
            metric_unit: str = kwargs['metric_unit']
            metric_min: Union[int, float] = kwargs['metric_min']
            metric_max: Union[int, float] = kwargs['metric_max']
            metric_key: str = kwargs['metric_key']

            customary_unit: str = kwargs['customary_unit']
            customary_min: Union[int, float] = kwargs['customary_min']
            customary_max: Union[int, float] = kwargs['customary_max']
            customary_key: str = kwargs['customary_key']

            # Create widget
            temp_col1, temp_col2 = st.columns(2)
            with temp_col1:
                min_unit_metric = st.number_input(
                    f'Min {metric_unit}',
                    value=metric_min,
                    disabled=st.session_state['metric_or_customary'] != 'Metric',
                    key=f'min_{metric_key}'
                )
                max_unit_metric = st.number_input(
                    f'Max {metric_unit}',
                    value=metric_max,
                    disabled=st.session_state['metric_or_customary'] != 'Metric',
                    key=f'max_{metric_key}'
                )
            with temp_col2:
                min_unit_customary = st.number_input(
                    f'Min {customary_unit}', value=customary_min,
                    disabled=st.session_state['metric_or_customary'] != 'Customary', key=f'min_{customary_key}'
                )
                max_unit_customary = st.number_input(
                    f'Max {customary_unit}', value=customary_max,
                    disabled=st.session_state['metric_or_customary'] != 'Customary', key=f'max_{customary_key}'
                )


@st.fragment(run_every=FRAGMENT_RERUN_SPEED)
def create_anomaly_settings() -> None:
    anomaly_col1, anomaly_col2, anomaly_col3, anomaly_col4, anomaly_col5, anomaly_col6 = st.columns(6)
    with anomaly_col1:
        create_anomaly_setting_widget(
            'Humidity Settings', generic=True, generic_unit='Percentage', generic_min=0, generic_max=100,
            generic_key='humidity'
        )
    with anomaly_col2:
        create_anomaly_setting_widget(
            'Precipitation Settings', generic=False, metric_unit='Millimeters', metric_min=0, metric_max=500,
            metric_key='precip_mm', customary_unit='Inches', customary_min=0, customary_max=20,
            customary_key='precip_in'
        )
    with anomaly_col3:
        create_anomaly_setting_widget(
            'Air Pressure Settings', generic=False, metric_unit='Millibars', metric_min=0, metric_max=2000,
            metric_key='pressure_mb', customary_unit='Inches', customary_min=0, customary_max=60,
            customary_key='pressure_in'
        )
    with anomaly_col4:
        create_anomaly_setting_widget(
            'Temperature Settings', generic=False, metric_unit='Celsius', metric_min=0, metric_max=100,
            metric_key='temp_c', customary_unit='Fahrenheit', customary_min=32, customary_max=212,
            customary_key='temp_f'
        )
    with anomaly_col5:
        create_anomaly_setting_widget(
            'UV Index Settings', generic=True, generic_unit='UV Index Score', generic_min=0, generic_max=11,
            generic_key='uv_index_score'
        )
    with anomaly_col6:
        create_anomaly_setting_widget(
            'Wind Speed Settings', generic=False, metric_unit='Meters per Second', metric_min=0, metric_max=500,
            metric_key='wind_kph', customary_unit='Miles per Hour', customary_min=0, customary_max=311,
            customary_key='wind_mph'
        )


@st.fragment(run_every=FRAGMENT_RERUN_SPEED)
def display_any_anomolies() -> None:
    # Get the historical data
    historical_data: Union[dict[str, list], None] = st.session_state.get('HISTORICAL_DATA', None)
    if historical_data is not None:
        st.write(historical_data)
    else:
        st.info('Historical Data is still loading.', icon="⏳")


def create_anomaly_tab() -> None:
    st.title('Anomaly Tracker')
    st.text('This section scans historical data for anomalies based on settings below.')
    st.text('Ranges you select are inclusive of edge numbers.')

    # Create settings to look for anomalies
    create_anomaly_settings()

    # Look for anomalies
    display_any_anomolies()


def update_data() -> None:
    global SENSOR_DATA, REAL_TIME_DATA, HISTORICAL_DATA
    while True:
        SENSOR_DATA = load_sensor_data()
        REAL_TIME_DATA = load_real_time_data()
        HISTORICAL_DATA = load_historical_data()
        sleep(DATA_UPDATE_SPEED)


@st.cache_data(ttl=DATA_UPDATE_SPEED)
def get_cached_sensor_data() -> Union[list[dict], None]:
    global SENSOR_DATA
    return SENSOR_DATA


@st.cache_data(ttl=DATA_UPDATE_SPEED)
def get_cached_real_time_data() -> Union[dict[str, list], None]:
    global REAL_TIME_DATA
    return REAL_TIME_DATA


@st.cache_data(ttl=DATA_UPDATE_SPEED)
def get_cached_historical_data() -> Union[dict[str, list], None]:
    global HISTORICAL_DATA
    return HISTORICAL_DATA


@st.fragment(run_every=DATA_UPDATE_SPEED)
def pass_data_updates() -> None:
    st.session_state['SENSOR_DATA'] = get_cached_sensor_data()
    st.session_state['REAL_TIME_DATA'] = get_cached_real_time_data()
    st.session_state['HISTORICAL_DATA'] = get_cached_historical_data()


def create_dashboard() -> None:
    # Create initial settings and title
    st.set_page_config(layout='wide')
    st.title('Weather Data Dashboard')

    # Start the data update thread
    data_update_thread = Thread(name='data_update_thread', target=update_data, daemon=True)
    data_update_thread.start()

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


if __name__ == '__main__':
    create_dashboard()
