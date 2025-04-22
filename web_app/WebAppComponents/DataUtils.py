import streamlit as st
from typing import Union
from datetime import datetime, timedelta
from requests import get, Response
from hashlib import sha256
from .Constants import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD_FILE, PROXY_HOST, PROXY_PORT, DATA_UPDATE_SPEED


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


@st.fragment(run_every=DATA_UPDATE_SPEED)
def pass_data_updates() -> None:
    st.session_state['SENSOR_DATA'] = load_sensor_data()
    st.session_state['REAL_TIME_DATA'] = load_real_time_data()
    st.session_state['HISTORICAL_DATA'] = load_historical_data()
