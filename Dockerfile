# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variables
ENV START_URL ""
ENV MAX_PAGES 5
ENV TV_SHOW_NAME ""
ENV DOWNLOAD_DIR "/usr/src/app/downloads"
ENV MAX_WORKERS 5

# Run the scraper with the environment variables
CMD ["sh", "-c", "python3 app.py \"$START_URL\" --max_pages \"$MAX_PAGES\" --tv_show_name \"$TV_SHOW_NAME\" --download_dir \"$DOWNLOAD_DIR\" --max_workers \"$MAX_WORKERS\""]