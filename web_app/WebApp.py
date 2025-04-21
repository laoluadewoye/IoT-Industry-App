import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from os import getenv
from hashlib import sha256
from requests import get, Response
from folium import Map as FoliumMap, Marker as FoliumMarker, CircleMarker as FoliumCircleMarker, Icon as FoliumIcon
from typing import Union
from collections import Counter
from datetime import datetime, timedelta

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


def load_data(content: dict[str, str]) -> Union[dict[str, list], list[dict], None]:
    # Send a get request to the proxy server
    response: Response = get(f'http://{PROXY_HOST}:{PROXY_PORT}/web_app', json=content, timeout=10)

    # Get json result
    response_json = response.json()
    if response_json['status'] != 'Success':
        st.error(response_json['message'])
        return None

    return response.json()['result']


@st.cache_data(ttl=9)
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


@st.fragment
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
    sensor_data: Union[list[dict], None] = load_sensor_data()
    if sensor_data is None:
        sensor_data = []

    sensor_list: list[str] = [document['sensor_name'] for document in sensor_data]

    # Create dropdown
    selected_sensors_disabled: bool = all_or_selected == 'All'
    selected_sensors = st.multiselect(
        'Select Sensors', sensor_list, default=sensor_list[0], disabled=selected_sensors_disabled,
        key='selected_sensors',
    )

    # Select the time range for historical and anomaly tabs
    st.subheader('Select Time Range')
    st.text('This feature is for viewing historical data and anomaly alerts.')

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


@st.fragment(run_every=3)
def create_sensor_map() -> st.map:
    # Create the map around the DMV
    vienna_coordinates: list[float] = [38.900692, -77.270946]
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
            new_marker: Union[FoliumMarker, FoliumCircleMarker] = FoliumMarker(
                [row['Latitude'], row['Longitude']],
                popup=popup_text,
                icon=FoliumIcon(color='red'),
            )
        else:
            new_marker: Union[FoliumMarker, FoliumCircleMarker] = FoliumCircleMarker(
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
    sensor_data: Union[list[dict], None] = load_sensor_data()
    if sensor_data is None:
        sensor_data = []

    sensor_list: list[list] = [
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


@st.fragment(run_every=3)
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
    real_time_data: Union[dict[str, list], None] = load_real_time_data()
    if real_time_data is not None:
        # Create metrics
        metric_keys: list[str] = list(real_time_data.keys())
        generic_metric_names: list[str] = [
            'Humidity', 'Precipitation', 'Pressure', 'Temperature', 'UV Index', 'Wind Degrees', 'Wind Direction',
            'Wind Speed'
        ]
        metric_modifiers: list[str] = list(st.session_state['unit_modifiers'])
        create_real_time_data_container(real_time_data, zip(metric_keys, generic_metric_names, metric_modifiers))


def find_county_name(name: str) -> str:
    try:
        return st.session_state['sensor_df'][st.session_state['sensor_df']['Sensor Name'] == name]['County'].values[0]
    except IndexError:
        return 'General'


def create_time_charts(historical_data: dict[str, list], metric_package: zip) -> None:
    for metric_key, metric_name, metric_modifier in metric_package:
        # Create time-zone aware dates
        start_date_str: Union[datetime, str] = st.session_state['start_date_time'] - timedelta(hours=4)
        end_date_str: Union[datetime, str] = st.session_state['end_date_time'] - timedelta(hours=4)

        start_date_str: str = start_date_str.strftime("%d %b %Y, %I:%M%p")
        end_date_str: str = end_date_str.strftime("%d %b %Y, %I:%M%p")

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


@st.fragment(run_every=3)
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
    historical_data: dict[str, list] = load_historical_data()
    if historical_data is not None:
        # Create metrics
        metric_keys: list[str] = list(historical_data.keys())
        generic_metric_names: list[str] = [
            'Humidity', 'Precipitation', 'Pressure', 'Temperature', 'UV Index', 'Wind Degrees', 'Wind Direction',
            'Wind Speed'
        ]
        metric_modifiers: list[str] = list(st.session_state['unit_modifiers'])
        create_time_charts(historical_data, zip(metric_keys, generic_metric_names, metric_modifiers))


def create_anomaly_tab() -> None:
    st.write('Anomaly Data')


# Create initial settings and title
st.set_page_config(layout='wide')
st.title('Weather Data Dashboard')

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
