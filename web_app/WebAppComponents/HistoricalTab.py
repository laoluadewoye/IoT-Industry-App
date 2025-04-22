import streamlit as st
from typing import Union
from datetime import datetime, timedelta
import pandas as pd
from .Constants import FRAGMENT_RERUN_SPEED


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
        city_names: list = historical_df['city'].unique().tolist()

        if metric_name == 'Wind Direction':
            # Create grouping table
            historical_df_groups = historical_df.groupby(['time_recorded', 'metric'])
            historical_df_size = historical_df_groups.size().unstack(fill_value=0)

            # Create area chart
            st.area_chart(historical_df_size, stack=True, x_label='Date & Time', y_label=f'Wind Direction')
        else:
            # Create pivot table
            if len(city_names) > 25:
                historical_df_grouped = historical_df.groupby(['county', 'time_recorded_est'])
                historical_df_avg = historical_df_grouped['metric'].mean().reset_index()
                historical_df_pivot = historical_df_avg.pivot(
                    index='time_recorded_est', columns='county', values='metric'
                )
            else:
                historical_df_pivot = historical_df.pivot(
                    index='time_recorded_est', columns='city', values='metric'
                )

            # Create line chart
            st.line_chart(historical_df_pivot, x_label='Date & Time', y_label=f'{metric_name} ({metric_modifier})')


@st.fragment(run_every=FRAGMENT_RERUN_SPEED)
def create_historical_tab() -> None:
    st.header('Historical Weather Data')
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
            sensor_desc: str = f'{cities_str}.'

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
