# ----------------------------------------------------------------------
# STAGE 1: Frontend Build 
# ----------------------------------------------------------------------
ARG NODE_VERSION=18
FROM node:${NODE_VERSION} AS frontend_build 

WORKDIR /app
# Copy only necessary files to leverage Docker's build cache
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm install
COPY frontend/ ./
RUN npm run build
# The built frontend static files are now in /app/frontend/dist

# ----------------------------------------------------------------------
# STAGE 2: Final Backend/Runtime Image
# ----------------------------------------------------------------------
FROM python:3.13-slim

# Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install PostgreSQL client library, poppler-utils (for pdf2image), and LibreOffice Impress (for PPTX→PDF conversion)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq-dev \
        poppler-utils \
        libreoffice-impress \
        libreoffice-common \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up the backend code directory
WORKDIR /code
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files (excluding frontend source, after installing requirements for better caching)
COPY . /code/

# Copy the built frontend static files from the previous stage (overwrite frontend folder)
COPY --from=frontend_build /app/frontend/dist /code/frontend/dist/

# Expose the FastAPI port
EXPOSE 8000

# Start the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "5"]