FROM hacky1610/emmanuelbase:1.3
COPY . /emmanuel/
RUN pip install Cython
RUN pip install -r /emmanuel/requirements.txt
ENTRYPOINT python3 /emmanuel/main.py