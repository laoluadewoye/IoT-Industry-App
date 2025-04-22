import streamlit as st
from collections import Counter
from typing import Union
from .Constants import FRAGMENT_RERUN_SPEED


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
    st.header('Latest Real Time Analytics')
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
            st.text(f'The averages are calculated from {cities_str}.')

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
