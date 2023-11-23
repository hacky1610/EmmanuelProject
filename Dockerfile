FROM hacky1610/emmanuelbase:v2.0

COPY . /emmanuel/
RUN pip install -r /emmanuel/requirements.txt
ENTRYPOINT python3 /emmanuel/main.py DEMO