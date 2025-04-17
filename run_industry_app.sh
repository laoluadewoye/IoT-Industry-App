#!/bin/bash

# Stop Docker Compose if it is already running
# docker-compose down -v

# Get the directory of the script and change to it
cd "$(dirname "$0")" || exit

# Create a folder called 'secrets' if it doesn't exist
mkdir -p secrets

# Generate password for database owner
uuidgen | tr -d '\n' > secrets/db_owner_password.txt

# Generate password for data generator
uuidgen | tr -d '\n' > secrets/data_gen_password.txt

# Generate password for web viewer
uuidgen | tr -d '\n' > secrets/web_view_password.txt

echo "Accounts created! Starting IoT weather app..."

# Run Docker Compose to start up the containers
# docker-compose up -d --build

# Print message after Docker Compose runs
echo "Docker Compose has been executed. The containers are now up and running."
echo "You can access the web app at http://localhost:8080."
echo "Give it a minute to come on if it isn't immediately accessible."
