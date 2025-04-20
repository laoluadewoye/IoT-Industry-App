import pandas as pd
from requests import get
from random import randint, seed
from datetime import datetime, timedelta
from tomllib import load
from copy import deepcopy
from os.path import dirname, abspath, join

# Read in configuration file
with open('create_data_config.toml', 'rb') as config_file:
    config: dict = load(config_file)

HISTORY_DAYS: int = config['history_days']
HISTORY_WEEKS: int = config['history_weeks']
HISTORY_MONTHS: int = config['history_months']
ZIPCODES_PATH: str = config['zipcodes_path']
API_KEY: str = config['api_key']
GET_AIR_QUALITY: str = config['get_air_quality']

# Get the folder the zipcodes are in
zipcodes_folder: str = dirname(abspath(ZIPCODES_PATH))

# Read in zipcodes
zipcodes_df: pd.DataFrame = pd.read_csv(ZIPCODES_PATH)

# Set up the date range
total_delta_days: int = HISTORY_DAYS + HISTORY_WEEKS * 7 + HISTORY_MONTHS * 30
end_date: datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
start_date: datetime = end_date - timedelta(days=total_delta_days)

# Iterate through zipcodes to create a list of randomized data
data_tuple_list: list[tuple] = []
for index, row in zipcodes_df.iterrows():
    # Create name of the sensor
    sensor_name: str = f'{row["zip_code"]}_{row["city"].replace(" ", "_").lower()}'

    # Loop through historical data
    cur_date: datetime = deepcopy(start_date)
    while cur_date <= end_date:
        # Create sensor link
        sensor_api_link: str = (
            f'http://api.weatherapi.com/v1/history.json?'
            f'key={API_KEY}&q={row["zip_code"]}&dt={cur_date.strftime("%Y-%m-%d")}&aqi={GET_AIR_QUALITY}'
        )

        # Get hour-by-hour data
        data_by_sensor: dict = get(url=sensor_api_link).json()
        data_by_sensor_location: dict = data_by_sensor['location']
        data_by_sensor_hour: list = data_by_sensor['forecast']['forecastday'][0]['hour']

        # Add hourly data to database in a random fashion
        for sensor_hour_info in data_by_sensor_hour:
            sensor_hour_timestamp: datetime = datetime.strptime(sensor_hour_info['time'], '%Y-%m-%d %H:%M')
            sensor_hour_tuple: tuple = (
                sensor_name, sensor_hour_timestamp, data_by_sensor_location['lat'], data_by_sensor_location['lon'],
                row['city'], f"{row['county']} County", row['state'], row['zip_code'], sensor_hour_info['temp_c'],
                sensor_hour_info['temp_f'], sensor_hour_info['wind_mph'], sensor_hour_info['wind_kph'],
                sensor_hour_info['wind_degree'], sensor_hour_info['wind_dir'], sensor_hour_info['pressure_mb'],
                sensor_hour_info['pressure_in'], sensor_hour_info['precip_mm'], sensor_hour_info['precip_in'],
                sensor_hour_info['humidity'], sensor_hour_info['uv']
            )
            seed(datetime.now().timestamp())
            rand_index: int = randint(0, len(data_tuple_list))
            data_tuple_list.insert(rand_index, sensor_hour_tuple)

        # Increment date by one day
        cur_date += timedelta(days=1)
        print(f'Created data for {sensor_name} on {cur_date}.')

# Turn the tuple list into a dataframe
data_df: pd.DataFrame = pd.DataFrame(data_tuple_list, columns=[
    'sensor_name', 'time_recorded', 'latitude', 'longitude', 'city', 'county', 'state', 'zip_code', 'temp_c', 'temp_f',
    'wind_mph', 'wind_kph', 'wind_degree', 'wind_dir', 'pressure_mb', 'pressure_in', 'precip_mm', 'precip_in',
    'humidity_perc', 'uv_index_score'
])

# Save the dataframe to a csv file
data_df.to_csv(join(zipcodes_folder, 'data_generator/zipcode_data.csv'), index=False)

# Sort then save again
data_df_sorted = data_df.sort_values(by=["sensor_name", "time_recorded"])
data_df_sorted.to_csv(join(zipcodes_folder, 'data_generator/zipcode_data_sorted.csv'), index=False)
