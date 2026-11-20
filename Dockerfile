FROM python:3.12-slim

ARG IMAGE_TAG=dev
ARG GIT_SHA=unknown
ARG BUILD_NUMBER=0
ENV IMAGE_TAG=${IMAGE_TAG} GIT_SHA=${GIT_SHA} BUILD_NUMBER=${BUILD_NUMBER} \
    PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CALC_DB_PATH=/tmp/calc_engine.db

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --no-create-home calc
COPY app ./app

USER 10001
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
