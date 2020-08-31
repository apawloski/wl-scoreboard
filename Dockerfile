FROM python:3-alpine

RUN python -m pip install --upgrade pip
COPY build_scoreboard.py scoreboard.html requirements.txt ./
RUN pip install -r requirements.txt


