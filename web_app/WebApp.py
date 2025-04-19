import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from os import getenv
from hashlib import sha256
from requests import get, Response

# Get core database environmental variables
local_defaults = {
    'DB_HOST': 'localhost', 'DB_PORT': '8000', 'DB_USER': 'web_view',
    'DB_PASSWORD_FILE': '../secrets/web_view_password.txt', 'PROXY_HOST': 'db-proxy-server', 'PROXY_PORT': '8079'
}
docker_defaults = {
    'DB_HOST': 'mongo-db', 'DB_PORT': '27017', 'DB_USER': 'web_view',
    'DB_PASSWORD_FILE': '../secrets/web_view_password.txt', 'PROXY_HOST': 'localhost', 'PROXY_PORT': '8079'
}
defaults = docker_defaults

DB_HOST: str = getenv('DB_HOST', defaults['DB_HOST'])
DB_PORT: str = getenv('DB_PORT', defaults['DB_PORT'])
DB_USER: str = getenv('DB_USER', defaults['DB_USER'])
DB_PASSWORD_FILE: str = getenv('DB_PASSWORD_FILE', defaults['DB_PASSWORD_FILE'])
PROXY_HOST: str = getenv('PROXY_HOST', defaults['PROXY_HOST'])
PROXY_PORT: str = getenv('PROXY_PORT', defaults['PROXY_PORT'])


@st.cache_data(max_entries=2)
def load_sensor_data() -> str:
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
    return response.content.decode()

@st.fragment
def create_filter_settings() -> None:
    st.header('Filter Settings')

    # Selection for which sensors to view
    st.subheader('Select Location Setting')
    all_or_selected = st.radio(
        'What locations would you like the average of?',
        ['All', 'Selected Options'],
        horizontal=True,
        key='all_or_selected'
    )

    # Select the sensors if 'selected' is selected
    if st.session_state['all_or_selected'] == 'Selected Options':
        st.subheader('Select Sensors to View')
        st.write(load_sensor_data())

    # Select what units you wish to use
    st.subheader('Select Unit of Measurement')
    metric_or_customary = st.radio(
        'What measurement system would you like to use?',
        ['Metric', 'Customary'],
        captions=['For international use.', 'Used in North America and UK.'],
        key='metric_or_customary'
    )


def create_sensor_tab() -> None:
    st.write('Sensor Data')


def create_real_time_tab() -> None:
    st.write('Real Time Data')


def create_historical_tab() -> None:
    st.write('Historical Data')


# Create initial settings and title
st.set_page_config(layout='wide')
# st_autorefresh(interval=5000, key='auto_refresh')
st.title('Weather Data Dashboard')

# Print environmental variables
st.write(f'DB_HOST: {DB_HOST}')
st.write(f'DB_PORT: {DB_PORT}')
st.write(f'DB_USER: {DB_USER}')
st.write(f'DB_PASSWORD_FILE: {DB_PASSWORD_FILE}')
st.write(f'PROXY_HOST: {PROXY_HOST}')
st.write(f'PROXY_PORT: {PROXY_PORT}')

# Create a sidebar
with st.sidebar:
    create_filter_settings()

# Create tabs
sensor_tab, real_time_tab, historical_tab = st.tabs(['Sensor Data', 'Real Time Data', 'Historical Data'])

with sensor_tab:
    create_sensor_tab()

with real_time_tab:
    create_real_time_tab()

with historical_tab:
    create_historical_tab()
