# Dockerfile
# Use the official Python image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install them
RUN apt-get update && apt-get install -y build-essential
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm
RUN python -c "import nltk; nltk.download('punkt')"
RUN python -c "import nltk; nltk.download('punkt_tab')"
# Copy the rest of the app
COPY ./app /app/app

# Expose the port FastAPI runs on
EXPOSE 8000
ENV PYTHONPATH=/app

# Run the app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

