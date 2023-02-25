FROM accetto/ubuntu-vnc-xfce-python-g3:vscode-firefox
COPY . /src
WORKDIR /src

USER root

# Pkgs for building `readline`
RUN apt-get update && apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl procps python3-dev

# Fonts
RUN apt-get -y -qq install fonts-droid-fallback ttf-wqy-zenhei ttf-wqy-microhei fonts-arphic-ukai fonts-arphic-uming fonts-emojione

# Install wrapper
RUN pip install -r requirements.txt
RUN python setup.py install

# Install browser
RUN python -m playwright install firefox
