FROM python:3.13

RUN apt-get update && apt-get -y install default-mysql-server

WORKDIR /code

RUN pip install --upgrade pip && pip install pipenv
ENV PIPENV_CUSTOM_VENV_NAME="commit-tracker"
COPY Pipfile ./
COPY Pipfile.lock ./
RUN pipenv install --dev