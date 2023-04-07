FROM python:3.7.16
COPY . /emmanuel/
RUN pip install -r /emmanuel/requirements.txt
ENTRYPOINT python3 /emmanuel/trade_once.py