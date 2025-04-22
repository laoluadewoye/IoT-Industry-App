import streamlit as st
from streamlit_folium import st_folium
from typing import Union
import pandas as pd
from folium import (Map as FoliumMap, Marker as FoliumMarker, CircleMarker as FoliumCircleMarker, Icon as FoliumIcon,
                    FeatureGroup as FoliumFeatureGroup)
from .Constants import FRAGMENT_RERUN_SPEED


@st.fragment(run_every=FRAGMENT_RERUN_SPEED)
def create_sensor_table() -> None:
    # Get data for the table
    sensor_data: Union[list[dict], None] = st.session_state.get('SENSOR_DATA', None)
    if sensor_data is None or len(sensor_data) == 0:
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
    st.header('Sensor Summary')
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
