import streamlit as st
from os import getenv

st.set_page_config(layout='wide')
st.title("Weather Data Dashboard")

envs = ['DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD_FILE', 'PROXY_HOST', 'PROXY_PORT']
for env in envs:
    env_value = getenv(env)
    if env_value is None:
        raise Exception(f'Environment variable {env} is not set.')
    else:
        st.write(f'{env}: {env_value}')
