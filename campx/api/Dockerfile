FROM python:3.13-slim

WORKDIR /app

# This image is built with ./campx/backend as the Docker build context,
# so requirements.txt is copied from campx/backend/requirements.txt.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
