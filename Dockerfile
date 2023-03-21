FROM accetto/ubuntu-vnc-xfce-python-g3:vscode-firefox

USER root

# Pkgs for building `readline`
RUN apt-get update && apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl procps python3-dev

# Fonts
RUN apt-get -y -qq install fonts-droid-fallback ttf-wqy-zenhei ttf-wqy-microhei fonts-arphic-ukai fonts-arphic-uming fonts-emojione

# Install browser and other pkgs (to cache things that do not change and speed up development)
RUN pip install playwright
RUN python -m playwright install firefox
RUN pip install readline

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

COPY . /src
WORKDIR /src

# Install wrapper
RUN python setup.py install

