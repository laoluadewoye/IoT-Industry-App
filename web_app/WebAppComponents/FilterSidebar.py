import streamlit as st
from typing import Union
from datetime import datetime, timedelta
from .Constants import FRAGMENT_RERUN_SPEED


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
    if sensor_data is not None and len(sensor_data) != 0:
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
