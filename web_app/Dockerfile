FROM python:3.13-slim

# Create a non-root user
RUN groupadd --system app && useradd --system --create-home --gid app app

# Set the working directory
WORKDIR /app

# Copy the current directory contents
COPY . .

# Change ownership of the app directory
RUN chown -R app:app /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Switch to the non-root user
USER app

# Run the app
ENTRYPOINT ["streamlit", "run", "WebApp.py"]
