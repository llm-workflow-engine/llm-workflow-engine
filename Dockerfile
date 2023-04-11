FROM accetto/ubuntu-vnc-xfce-python-g3:vscode-firefox

USER root

# Pkgs for default database
RUN apt-get update && apt-get install -y sqlite3

# Fonts
RUN apt-get -y -qq install fonts-droid-fallback ttf-wqy-zenhei ttf-wqy-microhei fonts-arphic-ukai fonts-arphic-uming fonts-emojione

COPY requirements.txt /tmp/requirements.txt

RUN pip install langchain
RUN pip install -r /tmp/requirements.txt

COPY . /src
WORKDIR /src

# Install wrapper
RUN pip install -e .

ENV PYTHONPATH=/src:$PYTHONPATH
