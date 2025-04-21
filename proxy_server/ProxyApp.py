from pymongo import MongoClient
from pymongo.database import Database, Collection
from pymongo.errors import OperationFailure, CollectionInvalid, ConnectionFailure
from pymongo.results import InsertOneResult
from os import getenv
import sys
from hashlib import sha256
from flask import Flask, jsonify, request, Response
from waitress import serve
from time import time
from datetime import datetime, UTC
from json import loads as json_loads
from typing import Union

# Get core database environmental variables
DB_HOST: str = getenv('DB_HOST')
DB_PORT: str = getenv('DB_PORT')
DB_OWNER: str = getenv('DB_OWNER')
DB_OWNER_PASSWORD_FILE: str = getenv('DB_OWNER_PASS_FILE')

# Get the other usernames
DATA_GEN: str = getenv('DATA_GEN')
WEB_VIEW: str = getenv('WEB_VIEW')

# Hash the passwords and save them to local file
HASHED_DATA_GEN_PASSWORD: str = sha256(open(getenv('DATA_GEN_PASSWORD_FILE')).read().encode()).hexdigest().strip()
HASHED_WEB_VIEW_PASSWORD: str = sha256(open(getenv('WEB_VIEW_PASSWORD_FILE')).read().encode()).hexdigest().strip()
with open('./hashed_passwords.txt', 'w') as hp_file:
    hp_file.writelines(
        [f'data_gen_password={HASHED_DATA_GEN_PASSWORD}\n', f'web_view_password={HASHED_WEB_VIEW_PASSWORD}\n']
    )

# Create flask app
app = Flask(__name__)
APP_START_TIME: float = time()

# Dictionary to maintain sensors
app_sensor_tracker: dict[int, list] = {}
app_sensor_mod: int = 20  # Calculated by sqrt(n), where n is the number of entries expected in the equation x + n/x

# List of sensor measurements
CUSTOMARY_MEASUREMENTS: list[str] = [
    'humidity_perc', 'precip_in', 'pressure_in', 'temp_f', 'uv_index_score', 'wind_degree', 'wind_dir', 'wind_mph'
]
METRIC_MEASUREMENTS: list[str] = [
    'humidity_perc', 'precip_mm', 'pressure_mb', 'temp_c', 'uv_index_score', 'wind_degree', 'wind_dir', 'wind_kph'
]


def create_database() -> None:
    # Create owner connection
    db_owner_password: str = open(DB_OWNER_PASSWORD_FILE).read()
    owner_conn_string: str = f'mongodb://{DB_OWNER}:{db_owner_password}@{DB_HOST}:{DB_PORT}/'
    owner_client: MongoClient = MongoClient(owner_conn_string, connectTimeoutMS=3000)

    # Create database object and try pinging it
    weather: Database = owner_client['weather']

    # Create data gen user
    try:
        weather.command(
            {'createUser': DATA_GEN, 'pwd': HASHED_DATA_GEN_PASSWORD, 'roles': [{'role': 'readWrite', 'db': 'weather'}]}
        )
    except OperationFailure:
        print('Data Generation user already exists.')

    # Create web view user
    try:
        weather.command(
            {'createUser': WEB_VIEW, 'pwd': HASHED_WEB_VIEW_PASSWORD, 'roles': [{'role': 'read', 'db': 'weather'}]}
        )
    except OperationFailure:
        print('Web View user already exists.')

    # Create time-series collections
    measurements = [
        'humidity_perc', 'precip_in', 'precip_mm', 'pressure_in', 'pressure_mb', 'temp_c',
        'temp_f', 'uv_index_score', 'wind_degree', 'wind_dir', 'wind_kph', 'wind_mph'
    ]
    for measurement in measurements:
        try:
            weather.create_collection(
                name=measurement,
                timeseries={
                    'timeField': 'time_recorded',
                    'metaField': 'sensor_name',
                    'granularity': 'hours'
                }
            )
            print(f'Time-series collection {measurement} created.')
        except CollectionInvalid:
            print(f'Time-series collection {measurement} already exists.')

    print('Database created!')

    # Close the connection
    owner_client.close()


def create_database_test() -> None:
    # Test
    global DB_HOST
    global DB_PORT
    DB_HOST = 'localhost'
    DB_PORT = '8000'
    db_owner: str = 'db_owner'
    db_owner_password_file: str = '../secrets/db_owner_password.txt'

    # Create owner connection
    db_owner_password: str = open(db_owner_password_file).read()
    owner_conn_string: str = f'mongodb://{db_owner}:{db_owner_password}@{DB_HOST}:{DB_PORT}/'
    owner_client: MongoClient = MongoClient(owner_conn_string, connectTimeoutMS=3000)

    # Create database object
    weather: Database = owner_client['weather']

    # Create data gen user
    weather.command(
        {'createUser': 'data_gen', 'pwd': 'data_gen_password', 'roles': [{'role': 'readWrite', 'db': 'weather'}]}
    )

    print('Database created!')

    # Close the connection
    owner_client.close()


@app.route('/status', methods=['GET'])
def status() -> tuple[Response, int]:
    uptime_seconds: int = int(time() - APP_START_TIME)
    status_info: dict = {
        'status': 'alive',
        'timestamp': datetime.now(UTC),
        'uptime_seconds': uptime_seconds,
    }
    return jsonify(status_info), 200


def insert_into_sensor_tracker(sensor_name: str) -> bool:
    # Get the zipcode for sorting
    sensor_info: list[str] = sensor_name.split('_')
    sensor_zipcode: int = int(sensor_info[0])

    # Sort the zipcode into
    sensor_already_existed: bool = False
    mod_location: int = sensor_zipcode % app_sensor_mod
    if mod_location in app_sensor_tracker:
        if sensor_name in app_sensor_tracker[mod_location]:
            sensor_already_existed = True
        else:
            app_sensor_tracker[mod_location].append(sensor_name)
    else:
        app_sensor_tracker[mod_location] = [sensor_name]

    return sensor_already_existed


@app.route('/data_gen', methods=['POST'])
def data_gen() -> tuple[Response, int]:
    # Access form fields from the POST request
    try:
        username: str = request.form.get('username')
        password: str = request.form.get('password')
        host: str = request.form.get('host')
        port: str = request.form.get('port')
        collection: str = request.form.get('collection')

        # Decode the document
        document: dict = json_loads(request.form.get('document'))

        # Convert the time field to utc datetime object
        document['time_recorded'] = datetime.strptime(document['time_recorded'], '%Y-%m-%d %H:%M:%S')
        document['time_recorded'] = document['time_recorded'].replace(tzinfo=UTC)
    except KeyError as e:
        return jsonify({'status': 'Error', 'message': f'Invalid request: Missing Form Field. {e}'}), 400
    except (ValueError, SyntaxError) as e:
        return jsonify({'status': 'Error', 'message': f'Invalid request: Invalid JSON Format. {e}'}), 400

    # Verify username and password
    if username != DATA_GEN or password != HASHED_DATA_GEN_PASSWORD:
        msg: str = 'Invalid request: Invalid username or password for data generation API call.'
        return jsonify({'status': 'Unauthorized', 'message': msg}), 401

    # Verify host and port
    if host != DB_HOST or port != DB_PORT:
        return jsonify({'status': 'Unauthorized', 'message': 'Invalid request: Invalid host or port.'}), 401

    # Access database on behalf of data generator
    try:
        data_gen_conn_string: str = f'mongodb://{DATA_GEN}:{HASHED_DATA_GEN_PASSWORD}@{DB_HOST}:{DB_PORT}/weather'
        data_gen_client: MongoClient = MongoClient(data_gen_conn_string, connectTimeoutMS=3000)
    except (ConnectionFailure, OperationFailure):
        msg: str = f'Authentication with MongoDB rejected.'
        return jsonify({'status': 'Unauthorized', 'message': msg}), 403

    # Insert the document into the connection
    try:
        cur_collection: Collection = data_gen_client['weather'][collection]
        insert_result: InsertOneResult = cur_collection.insert_one(document)
    except OperationFailure:
        msg: str = f'Post request to do MongoDB insert operation with collection {collection} failed.'
        return jsonify({'status': 'Error', 'message': msg}), 400

    # Add a new sensor to a collection of sensors if it does not exist
    exist_status: bool = insert_into_sensor_tracker(document['sensor_name'])
    if not exist_status:
        try:
            sensor_collection: Collection = data_gen_client['weather']['sensors']
            sensor_result = sensor_collection.find_one({'sensor_name': document['sensor_name']})
            if sensor_result is None:
                sensor_collection.insert_one({
                    'sensor_name': document['sensor_name'],
                    'latitude': document['latitude'],
                    'longitude': document['longitude'],
                    'city': document['city'],
                    'county': document['county'],
                    'state': document['state'],
                    'zip_code': document['zip_code']
                })
            attempted_sensor_insert: bool = True
        except OperationFailure:
            msg: str = f'Post request to do MongoDB insert operation with collection sensors failed.'
            return jsonify({'status': 'Error', 'message': msg}), 400
    else:
        sensor_result = None
        attempted_sensor_insert: bool = False

    if not exist_status and sensor_result is None and attempted_sensor_insert:
        sensor_msg: str = f'Sensor {document["sensor_name"]} has been added to local cache and database.'
    elif not exist_status and sensor_result is not None and attempted_sensor_insert:
        sensor_msg: str = f'Sensor {document["sensor_name"]} has been added to local cache but not database.'
    else:
        sensor_msg: str = f'Sensor {document["sensor_name"]} already exists in local cache.'

    # Return success
    msg: str = (
        f'Post request to do MongoDB insert operation succeeded.\n'
        f'Acknowledgement: {insert_result.acknowledged}.\n'
        f'Document ID: {insert_result.inserted_id}.\n'
        f'Sensor Status: {sensor_msg}'
    )
    return jsonify({'status': 'Success', 'message': msg}), 201


def get_latest_measurements(client: MongoClient, measurements: list[str], all_or_selected: str,
                            selected_sensors: list[str]) -> dict[str, list]:
    # Start measurement super dictionary
    latest_measurements: dict[str, list] = {}

    # Get a list of the latest measurement for each sensor for each measurement
    for measurement in measurements:
        # Create the measurement pipeline based on filter settings
        if all_or_selected in ['All', 'Empty'] or 'Empty' in selected_sensors:
            measurement_pipeline: list = [
                {'$sort': {'time_recorded': -1}},
                {'$group': {'_id': '$sensor_name', 'latest_value': {'$first': '$metric'}}}
            ]
        else:
            measurement_pipeline: list = [
                {'$match': {'sensor_name': {'$in': selected_sensors}}},
                {'$sort': {'time_recorded': -1}},
                {'$group': {'_id': '$sensor_name', 'latest_value': {'$first': '$metric'}}}
            ]

        # Use aggregate pipeline to get the latest recorded value for each sensor
        cur_collection: Collection = client['weather'][measurement]
        latest_record: list[dict] = cur_collection.aggregate(measurement_pipeline, allowDiskUse=True).to_list()

        # Save the list of results to super dictionary
        latest_measurements[measurement] = latest_record

    return latest_measurements


def get_historical_measurements(client: MongoClient, measurements: list[str], all_or_selected: str,
                                selected_sensors: list[str], start_date_time: datetime,
                                end_date_time: datetime) -> dict[str, list]:
    # Start measurement super dictionary
    historical_measurements: dict[str, list] = {}

    # Get a list of the latest measurement for each sensor for each measurement
    for measurement in measurements:
        # Create the measurement pipeline based on filter settings
        if all_or_selected in ['All', 'Empty'] or 'Empty' in selected_sensors:
            # measurement_pipeline: list = [
            #     {'$match': {'time_recorded': {'$gte': start_date_time, '$lte': end_date_time}}},
            #     {'$sort': {'time_recorded': -1}},
            #     {'$project': {'sensor_name': 1, 'time_recorded': 1}},
            #     {'$group': {'_id': '$sensor_name'}}
            # ]
            measurement_pipeline: list = [
                {'$match': {'time_recorded': {'$gte': start_date_time, '$lte': end_date_time}}},
                {'$sort': {'time_recorded': -1}},
                {'$project': {'_id': 0, 'sensor_name': 1, 'time_recorded': 1, 'metric': 1}},
            ]
        else:
            measurement_pipeline: list = [
                {'$match': {
                    'sensor_name': {'$in': selected_sensors},
                    'time_recorded': {'$gte': start_date_time, '$lte': end_date_time}
                }},
                {'$sort': {'time_recorded': -1}},
                {'$project': {'_id': 0, 'sensor_name': 1, 'time_recorded': 1, 'metric': 1}},
            ]

        # Use aggregate pipeline to get the latest recorded value for each sensor
        cur_collection: Collection = client['weather'][measurement]
        historical_record: list[dict] = cur_collection.aggregate(measurement_pipeline, allowDiskUse=True).to_list()

        # Save the list of results to super dictionary
        historical_measurements[measurement] = historical_record

    return historical_measurements


@app.route('/web_app', methods=['GET'])
def web_app() -> tuple[Response, int]:
    # Access arg fields from the Get request
    try:
        json_content: dict = request.get_json(force=True)
        purpose: int = int(json_content['purpose'])  # 0 for sensors, 1 for real time, 2 for historical
        username: str = json_content['username']
        password: str = json_content['password']
        host: str = json_content['host']
        port: str = json_content['port']

        # Get filters if desired
        if purpose != 0:
            filters: Union[dict, None] = json_content['filters']
        else:
            filters: Union[dict, None] = None

        # Get time range if desired
        if purpose == 2:
            time_range: Union[dict, None] = json_content['time_range']
            time_range['start_date_time'] = datetime.strptime(time_range['start_date_time'], '%Y-%m-%d %H:%M:%S')
            time_range['start_date_time'] = time_range['start_date_time'].replace(tzinfo=UTC)
            time_range['end_date_time'] = datetime.strptime(time_range['end_date_time'], '%Y-%m-%d %H:%M:%S')
            time_range['end_date_time'] = time_range['end_date_time'].replace(tzinfo=UTC)
        else:
            time_range: Union[dict, None] = None
    except KeyError as e:
        return jsonify({'status': 'Error', 'message': f'Invalid request: Missing Form Field. {e}'}), 400
    except (ValueError, SyntaxError) as e:
        return jsonify({'status': 'Error', 'message': f'Invalid request: Invalid JSON Format. {e}'}), 400

    # Verify username and password
    if username != WEB_VIEW or password != HASHED_WEB_VIEW_PASSWORD:
        msg: str = 'Invalid request: Invalid username or password for web view API call.'
        return jsonify({'status': 'Unauthorized', 'message': msg}), 401

    # Verify host and port
    if host != DB_HOST or port != DB_PORT:
        return jsonify({'status': 'Unauthorized', 'message': 'Invalid request: Invalid host or port.'}), 401

    # Access database on behalf of web viewer
    try:
        web_view_conn_string: str = f'mongodb://{WEB_VIEW}:{HASHED_WEB_VIEW_PASSWORD}@{DB_HOST}:{DB_PORT}/weather'
        web_view_client: MongoClient = MongoClient(web_view_conn_string, connectTimeoutMS=3000)
    except (ConnectionFailure, OperationFailure):
        msg: str = f'Authentication with MongoDB rejected.'
        return jsonify({'status': 'Unauthorized', 'message': msg}), 403

    # Complete the desired operation
    operation_result: Union[dict, list] = {'I am': 'a teapot'}
    try:
        if purpose not in [0, 1, 2]:  # Make sure the purpose is valid
            raise KeyError(f'Purpose {purpose} is not a valid purpose setting.')
        elif purpose == 0:  # Only do if the purpose is for sensor information retrieval
            cur_collection: Collection = web_view_client['weather']['sensors']
            operation_result: Union[dict, list] = cur_collection.find().to_list()
            for document in operation_result:
                document['_id'] = str(document['_id'])
        elif purpose == 1:  # Only do if the purpose is for real-time information retrieval
            # Select the measurement system to use
            if filters['metric_or_customary'] in ['Metric', 'Empty']:
                cur_measurements: list[str] = METRIC_MEASUREMENTS
            else:
                cur_measurements: list[str] = CUSTOMARY_MEASUREMENTS

            # Obtain real-time data
            operation_result: Union[dict, list] = get_latest_measurements(
                web_view_client, cur_measurements, filters['all_or_selected'], filters['selected_sensors']
            )
        elif purpose == 2:  # Only do if the purpose is for historical information retrieval
            # Select the measurement system to use
            if filters['metric_or_customary'] in ['Metric', 'Empty']:
                cur_measurements: list[str] = METRIC_MEASUREMENTS
            else:
                cur_measurements: list[str] = CUSTOMARY_MEASUREMENTS

            # Obtain historical data
            operation_result: Union[dict, list] = get_historical_measurements(
                web_view_client, cur_measurements, filters['all_or_selected'], filters['selected_sensors'],
                time_range['start_date_time'], time_range['end_date_time']
            )
    except (TypeError, OperationFailure) as e:
        msg: str = f'Get request to do MongoDB select operation of category {purpose} failed. Reason: {e}'
        return jsonify({'status': 'Error', 'message': msg}), 400
    except KeyError as e:
        msg: str = (
            f'Get request to do MongoDB select operation of category {purpose} failed. '
            f'Invalid purpose for web viewer API call. {e}'
        )
        return jsonify({'status': 'Error', 'message': msg}), 400

    msg: str = f'Get request to do MongoDB select operation of category {purpose} succeeded.'
    return jsonify({'status': 'Success', 'message': msg, 'result': operation_result}), 200


if __name__ == "__main__":
    # Force the output to appear
    sys.stdout.flush()

    # Create the database
    create_database()

    # Run the flask app
    serve(app, host='0.0.0.0', port=8079)
