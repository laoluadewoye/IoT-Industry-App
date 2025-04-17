import pandas as pd
import numpy as np
from time import sleep
from os import getenv
from requests import post, Response
from hashlib import sha256
from typing import Union
from datetime import datetime

# Get core database environmental variables
DB_HOST: str = getenv('DB_HOST')
DB_PORT: str = getenv('DB_PORT')
DB_USER: str = getenv('DB_USER')
DB_PASSWORD_FILE: str = getenv('DB_PASSWORD_FILE')
PROXY_HOST: str = getenv('PROXY_HOST')
PROXY_PORT: str = getenv('PROXY_PORT')


def row_to_dict(row: pd.Series) -> dict:
    # Define which columns to split out
    id_cols: list[str] = [
        'sensor_name', 'time_recorded', 'latitude', 'longitude',
        'city', 'county', 'state', 'zip_code'
    ]

    # Everything else becomes metrics
    metric_cols: list[str] = [col for col in row.index if col not in id_cols]

    # Make base metadata dict
    base_info: dict = row[id_cols].to_dict()

    # Build the super-dictionary
    super_dict: dict = {}
    for metric in metric_cols:
        # Create the sub dictionary
        sub_dict: dict = {**base_info, 'metric': row[metric]}

        # Turn numpy types into python types
        for key in sub_dict.keys():
            if isinstance(sub_dict[key], Union[np.float64, np.int64]):
                sub_dict[key] = sub_dict[key].item()

        # Add an updated datetime object
        # sub_dict['time_recorded'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Add to super-dictionary
        super_dict[metric] = sub_dict

    return super_dict


def send_data(collection_name: str, document: dict):
    # Create password hash
    hashed_data_gen_password: str = sha256(open(DB_PASSWORD_FILE).read().encode()).hexdigest()

    # Create message content
    content: dict = {
        'username': DB_USER,
        'password': hashed_data_gen_password,
        'host': DB_HOST,
        'port': DB_PORT,
        'collection': collection_name,
        'document_str': str(document)
    }

    # Send a post request to the proxy server
    response: Response = post(f'http://{PROXY_HOST}:{PROXY_PORT}/data_gen', data=content, timeout=10)
    print(f'Response code: {response.status_code}')
    print(f'Response text: {response.content.decode()}')


def read_in_data():
    data_df: pd.DataFrame = pd.read_csv('zipcode_data_sorted.csv')
    unique_sensors: np.ndarray = data_df["sensor_name"].unique()

    while True:
        for sensor_name in unique_sensors:
            # Get the first id of the sensor
            try:
                sensor_df: pd.DataFrame = data_df[data_df["sensor_name"] == sensor_name]
                first_id = sensor_df.index[0]
            except IndexError:
                print(f'All data for {sensor_name} has been sent.')
                continue

            # Use the id to pop a row out of the whole dataframe
            popped_row: pd.Series = data_df.iloc[first_id]
            data_df = data_df.drop(first_id, axis=0).reset_index(drop=True)

            # Turn it into a super-dictionary
            popped_row_set: dict[str, dict] = row_to_dict(popped_row)

            # Send it to the database
            for metric, metric_dict in popped_row_set.items():
                print(f'Sending {sensor_name}_{metric}...')
                send_data(metric, metric_dict)

            # Small delay
            sleep(0.01)

        # Break if there is no more data
        if len(data_df) <= 0:
            break

    print('All data has been sent.')


if __name__ == '__main__':
    read_in_data()
