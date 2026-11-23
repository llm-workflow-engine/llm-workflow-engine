FROM python:3

USER root

# Pkgs for default database.
RUN apt-get update && apt-get install -y sqlite3

# Editor packages.
RUN apt-get install -y vim vim-airline vim-ctrlp

COPY . /src
WORKDIR /src

# Install LWE
RUN pip install -e .

ENV PYTHONPATH=/src:$PYTHONPATH
