FROM selenium/standalone-chrome
COPY . /emmanuel/
RUN pip install -r /emmanuel/requirements.txt
ENTRYPOINT python3 /emmanuel/zulu_tradesh .py