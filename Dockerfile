## Image to build from sources

FROM debian:jessie
MAINTAINER XiVO Team "dev@avencall.com"

ENV DEBIAN_FRONTEND noninteractive
ENV HOME /root

# Add dependencies
RUN apt-get -qq update
RUN apt-get -qq -y install \
    git \
    apt-utils \
    python-pip \
    python-dev \
    libpq-dev \
    libyaml-dev

# Install xivo-call-logd
WORKDIR /usr/src
ADD . /usr/src/call-logd
WORKDIR call-logd
RUN pip install -r requirements.txt
RUN python setup.py install

# Configure environment
RUN touch /var/log/xivo-call-logd.log
RUN mkdir -p /etc/xivo-call-logd
RUN mkdir /var/lib/xivo-call-logd
RUN cp -a etc/xivo-call-logd/config.yml /etc/xivo-call-logd/
WORKDIR /root

# Clean
RUN apt-get clean
RUN rm -rf /usr/src/call-logd

CMD xivo-call-logd -f
