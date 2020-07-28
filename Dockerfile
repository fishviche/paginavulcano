FROM python:3.7-alpine

WORKDIR /app

COPY ./requirements.txt .

ENV PATH=/root/.local/bin:$PATH

RUN pip install -r requirements.txt --user

