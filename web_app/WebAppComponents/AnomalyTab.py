import streamlit as st
from typing import Union
from datetime import datetime, timedelta
from .Constants import FRAGMENT_RERUN_SPEED


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
            sensor_desc: str = f'{cities_str}.'


    # Create time-zone aware dates
    start_date_str: Union[datetime, str] = st.session_state['start_date_time'] - timedelta(hours=4)
    end_date_str: Union[datetime, str] = st.session_state['end_date_time'] - timedelta(hours=4)

    start_date_str = start_date_str.strftime("%d %b %Y, %I:%M%p")
    end_date_str = end_date_str.strftime("%d %b %Y, %I:%M%p")

    st.subheader(f'The following charts display information from {sensor_desc} '
                 f'during the time range of {start_date_str} to {end_date_str}.')

    # Create the settings dropdowns
    anomaly_col1, anomaly_col2, anomaly_col3, anomaly_col4, anomaly_col5, anomaly_col6 = st.columns(6)
    with anomaly_col1:
        create_anomaly_setting_widget(
            'Humidity Settings', generic=True, generic_unit='Percentage', generic_min=0, generic_max=100,
            generic_key='humidity_perc'
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


def check_metric_for_anomalies(historical_data: [dict[str, list]], metric_name: str, metric_title: str) -> None:
    # Print a title
    st.subheader(f'{metric_title.title()} Anomalies')

    # Check for humidity anomalies
    warning_count: int = 0
    minimum_metric: Union[int, float] = st.session_state[f'min_{metric_name}']
    maximum_metric: Union[int, float] = st.session_state[f'max_{metric_name}']

    for document in historical_data[metric_name]:
        below_min: bool = document['metric'] < minimum_metric
        above_max: bool = document['metric'] > maximum_metric
        if below_min or above_max:
            # Determine anomaly description
            if below_min:
                anomaly_desc = 'below'
                anomaly_edgepoint = 'minimum'
                anomaly_metric = minimum_metric
            elif above_max:
                anomaly_desc = 'above'
                anomaly_edgepoint = 'maximum'
                anomaly_metric = maximum_metric
            else:
                anomaly_desc = ''
                anomaly_edgepoint = ''
                anomaly_metric = None

            # Create warning message
            warning_msg = (f'{metric_title.title()} anomaly detected at {document["city"]} ({document["county"]}) '
                           f'at {document["time_recorded"]}. '
                           f'Current {metric_title.lower()} of {document["metric"]} is '
                           f'{anomaly_desc} the {anomaly_edgepoint} of {anomaly_metric}.')
            st.warning(warning_msg, icon='⚠️')
            warning_count += 1

    # Display no warning message if no anomalies were found
    if warning_count == 0:
        st.success(f'No {metric_title.lower()} anomalies detected.', icon='✅')


@st.fragment(run_every=FRAGMENT_RERUN_SPEED)
def display_any_anomolies() -> None:
    # Get the historical data
    historical_data: Union[dict[str, list], None] = st.session_state.get('HISTORICAL_DATA', None)
    if historical_data is not None:
        # Check for humidity anomalies
        check_metric_for_anomalies(historical_data, 'humidity_perc', 'Humidity Percentage')

        # Check for precipitation anomalies
        if st.session_state['metric_or_customary'] == 'Metric':
            precip_params = ['precip_mm', 'Precipitation (Millimeters)']
        else:
            precip_params = ['precip_in', 'Precipitation (Inches)']
        check_metric_for_anomalies(historical_data, *precip_params)

        # Check for air pressure anomalies
        if st.session_state['metric_or_customary'] == 'Metric':
            pressure_params = ['pressure_mb', 'Air Pressure (Millibars)']
        else:
            pressure_params = ['pressure_in', 'Air Pressure (Inches)']
        check_metric_for_anomalies(historical_data, *pressure_params)

        # Check for temperature anomalies
        if st.session_state['metric_or_customary'] == 'Metric':
            temp_params = ['temp_c', 'Temperature (Celsius)']
        else:
            temp_params = ['temp_f', 'Temperature (Fahrenheit)']
        check_metric_for_anomalies(historical_data, *temp_params)

        # Check for UV Index anomalies
        check_metric_for_anomalies(historical_data, 'uv_index_score', 'UV Index Score')

        # Check for wind speed anomalies
        if st.session_state['metric_or_customary'] == 'Metric':
            wind_params = ['wind_kph', 'Wind Speed (KPH)']
        else:
            wind_params = ['wind_mph', 'Wind Speed (MPH)']
        check_metric_for_anomalies(historical_data, *wind_params)
    else:
        st.info('Historical Data is still loading.', icon="⏳")


def create_anomaly_tab() -> None:
    st.header('Anomaly Tracker')
    st.text('This section scans historical data for anomalies based on settings below.')
    st.text('Ranges you select are inclusive of edge numbers.')

    # Create settings to look for anomalies
    create_anomaly_settings()

    # Look for anomalies
    display_any_anomolies()
