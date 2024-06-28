FROM python:3

USER root

# Pkgs for default database.
# Workaround for installing newer Rust compiler
ENV PATH="/root/.cargo/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends curl gcc &&  curl https://sh.rustup.rs -sSf | sh -s -- -y && apt-get install --reinstall libc6-dev -y

# Editor packages.
RUN apt-get install -y sqlite3 vim vim-airline vim-ctrlp

COPY requirements.txt /tmp/requirements.txt


RUN pip install --upgrade pip & \
    pip install -r /tmp/requirements.txt

COPY . /src
WORKDIR /src

# Install LWE
RUN pip install -e .

ENV PYTHONPATH=/src:$PYTHONPATH
