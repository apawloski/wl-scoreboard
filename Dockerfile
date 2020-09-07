FROM python:3-alpine

RUN python -m pip install --upgrade pip
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY build_scoreboard.py scoreboard.html ./

