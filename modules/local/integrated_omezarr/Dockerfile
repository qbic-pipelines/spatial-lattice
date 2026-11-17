FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends procps && rm -rf /var/lib/apt/lists/*
COPY modules/local/integrated_omezarr/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY bin/integrate_omezarr.py /usr/local/bin/integrate_omezarr.py
COPY bin/rami2d_rfc5.py /usr/local/bin/rami2d_rfc5.py
