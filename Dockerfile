FROM hacky1610/emmanuelbase:v1.0
COPY . /emmanuel/
RUN pip install -r /emmanuel/requirements.txt
ENTRYPOINT python3 /emmanuel/trade_once.py