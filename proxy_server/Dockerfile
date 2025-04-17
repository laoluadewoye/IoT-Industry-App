FROM python:3.13-alpine

# Create an app user
RUN addgroup -S app && adduser -S app -G app

# Set the working directory to /app and make app the owner
WORKDIR /app
RUN chown -R app:app /app

# Copy the current directory contents into the container at /app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set the user to app
USER app

# Run the program
ENTRYPOINT ["python", "ProxyApp.py"]
