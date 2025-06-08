# Use official Python image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the API source code
COPY api.py .

# Expose port (adjust if your api.py uses a different port)
EXPOSE 8000

# Set the default command to run the API
CMD ["python", "api.py"]
