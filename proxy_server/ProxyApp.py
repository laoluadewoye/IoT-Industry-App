from pymongo import MongoClient
from pymongo.database import Database, Collection
from pymongo.errors import OperationFailure, CollectionInvalid, ConnectionFailure
from pymongo.results import InsertOneResult
from pymongo.cursor import Cursor
from os import getenv
from hashlib import sha256
from flask import Flask, jsonify, request, Response
from waitress import serve
from time import time
from datetime import datetime, UTC
from ast import literal_eval
import bson

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
        'temp_c', 'temp_f', 'wind_mph', 'wind_kph', 'wind_degree', 'wind_dir', 'pressure_mb', 'pressure_in',
        'precip_mm', 'precip_in', 'humidity_perc', 'uv_index_score'
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


@app.route('/status', methods=['GET'])
def status() -> tuple[Response, int]:
    uptime_seconds: int = int(time() - APP_START_TIME)
    status_info: dict = {
        'status': 'alive',
        'timestamp': datetime.now(UTC),
        'uptime_seconds': uptime_seconds,
    }
    return jsonify(status_info), 200


@app.route('/data_gen', methods=['POST'])
def data_gen() -> tuple[Response, int]:
    # Access form fields from the POST request
    try:
        username: str = request.form.get('username')
        password: str = request.form.get('password')
        host: str = request.form.get('host')
        port: str = request.form.get('port')
        collection: str = request.form.get('collection')
        document_str: str = request.form.get('document_str')

        # Decode the document
        document: dict = literal_eval(document_str)

        # Convert the time field to utc datetime object
        document['time_recorded'] = datetime.strptime(document['time_recorded'], '%Y-%m-%d %H:%M:%S')
        document['time_recorded'] = document['time_recorded'].replace(tzinfo=UTC)
    except KeyError:
        return jsonify({'status': 'Error', 'message': 'Invalid request: Missing Form Field.'}), 400
    except (ValueError, SyntaxError):
        return jsonify({'status': 'Error', 'message': 'Invalid request: Invalid JSON Format.'}), 400

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
                    'longitude': document['longitude']
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


@app.route('/web_app/<purpose>', methods=['GET'])
def web_app(purpose: str) -> tuple[Response, int]:
    # Access arg fields from the Get request
    try:
        username: str = request.args.get('username')
        password: str = request.args.get('password')
        host: str = request.args.get('host')
        port: str = request.args.get('port')
    except KeyError:
        return jsonify({'status': 'Error', 'message': 'Invalid request: Missing Form Field.'}), 400

    # Verify username and password
    if username != WEB_VIEW or password != HASHED_WEB_VIEW_PASSWORD:
        msg: str = 'Invalid request: Invalid username or password for data generation API call.'
        return jsonify({'status': 'Unauthorized', 'message': msg}), 401

    # Verify host and port
    if host != DB_HOST or port != DB_PORT:
        return jsonify({'status': 'Unauthorized', 'message': 'Invalid request: Invalid host or port.'}), 401

    # Access database on behalf of data generator
    try:
        web_view_conn_string: str = f'mongodb://{WEB_VIEW}:{HASHED_WEB_VIEW_PASSWORD}@{DB_HOST}:{DB_PORT}/weather'
        web_view_client: MongoClient = MongoClient(web_view_conn_string, connectTimeoutMS=3000)
    except (ConnectionFailure, OperationFailure):
        msg: str = f'Authentication with MongoDB rejected.'
        return jsonify({'status': 'Unauthorized', 'message': msg}), 403

    # Complete the desired operation
    try:
        if purpose == 'sensors':
            cur_collection: Collection = web_view_client['weather']['sensors']
            operation_result: list = cur_collection.find().to_list()
            for document in operation_result:
                document['_id'] = str(document['_id'])
        else:
            raise KeyError
    except (TypeError, OperationFailure) as e:
        msg: str = f'Get request to do MongoDB select operation of category {purpose} failed. Reason: {e}'
        return jsonify({'status': 'Error', 'message': msg}), 400
    except KeyError:
        msg: str = (
            f'Get request to do MongoDB select operation of category {purpose} failed. '
            f'Invalid purpose for data generation API call.'
        )
        return jsonify({'status': 'Error', 'message': msg}), 400

    msg: str = f'Get request to do MongoDB select operation of category {purpose} succeeded.'
    return jsonify({'status': 'Success', 'message': msg, 'result': operation_result}), 200


if __name__ == "__main__":
    # Create the database
    create_database()

    # Run the flask app
    serve(app, host='0.0.0.0', port=8079)
