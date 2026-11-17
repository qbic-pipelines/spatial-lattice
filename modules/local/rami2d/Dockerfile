FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends git procps libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
# Source pinned to the version whose CLI and output layout this adapter targets.
RUN pip install --timeout 180 --no-cache-dir 'rami2d @ git+https://github.com/VictorDidier/RAMI2D.git@f6c4cc0f48dbd86b866ade8d3bf67177dd45712f'
COPY bin/rami2d_provenance.py /usr/local/bin/rami2d_provenance.py
RUN chmod +x /usr/local/bin/rami2d_provenance.py && rami2d-register --version && rami2d-transform --version
