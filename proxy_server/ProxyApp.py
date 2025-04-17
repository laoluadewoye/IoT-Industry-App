from pymongo import MongoClient
from pymongo.database import Database, Collection
from pymongo.errors import OperationFailure, CollectionInvalid, ConnectionFailure
from os import getenv
from hashlib import sha256
from flask import Flask, jsonify, Response, request
from waitress import serve
from time import time
from datetime import datetime, UTC
from ast import literal_eval

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


def create_database():
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


def create_database_test():
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


@app.route('/status', methods=['GET'])
def status():
    uptime_seconds = int(time() - APP_START_TIME)
    status_info = {
        'status': 'alive',
        'timestamp': datetime.now(UTC),
        'uptime_seconds': uptime_seconds,
    }
    return jsonify(status_info), 200


@app.route('/data_gen', methods=['POST'])
def data_gen():
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
        data_gen_conn_string = f'mongodb://{DATA_GEN}:{HASHED_DATA_GEN_PASSWORD}@{DB_HOST}:{DB_PORT}/weather'
        data_gen_client: MongoClient = MongoClient(data_gen_conn_string, connectTimeoutMS=3000)
    except (ConnectionFailure, OperationFailure):
        msg: str = f'Authentication with MongoDB rejected.'
        return jsonify({'status': 'Unauthorized', 'message': msg}), 403

    # Insert the document into the connection
    try:
        cur_collection: Collection = data_gen_client['weather'][collection]
        result = cur_collection.insert_one(document)
    except OperationFailure:
        msg: str = f'Post request to do MongoDB insert operation with collection {collection} failed.'
        return jsonify({'status': 'Error', 'message': msg}), 400

    # Return success
    msg: str = (
        f'Post request to do MongoDB insert operation succeeded. '
        f'Acknowledgement: {result.acknowledged}. Document ID: {result.inserted_id}'
    )
    return jsonify({'status': 'success', 'message': msg}), 201


if __name__ == "__main__":
    # Create the database
    create_database()

    # Run the flask app
    serve(app, host='0.0.0.0', port=8079)
