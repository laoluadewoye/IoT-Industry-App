@echo off

:: Stop Docker Compose if it is already running
docker-compose down -v

:: Get the directory of the script and change to it
cd /d "%~dp0"

:: Create a folder called 'secrets' if it doesn't exist
if not exist secrets mkdir secrets

:: Generate password for database user
powershell -Command^
 "[System.Guid]::NewGuid().ToString() | Set-Content -Path 'secrets/db_owner_password.txt' -NoNewline"

:: Generate password for data generator
powershell -Command^
 "[System.Guid]::NewGuid().ToString() | Set-Content -Path 'secrets/data_gen_password.txt' -NoNewline"

:: Generate password for web viewer
powershell -Command^
 "[System.Guid]::NewGuid().ToString() | Set-Content -Path 'secrets/web_view_password.txt' -NoNewline"

echo Accounts created! Starting IoT weather app...

:: Run Docker Compose to start up the containers
docker-compose up -d --build

:: Print message after Docker Compose runs
echo Docker Compose has been executed. The containers are now up and running.
echo You can access the web app at http://localhost:8080.
echo Give it a minute to come on if it isn't immediately available.
