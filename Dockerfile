FROM selenium/standalone-chrome:114.0-chromedriver-114.0


USER root
RUN apt-get update && apt-get install python3-distutils -y
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3 get-pip.py
RUN python3 -m pip install selenium

ENV TZ="Europe/Berlin"

COPY . /emmanuel/
RUN pip install -r /emmanuel/requirements.txt
ENTRYPOINT python3 /emmanuel/zulu_trade.py