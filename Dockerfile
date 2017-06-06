FROM python:3.4.2
MAINTAINER Wazo Maintainers <dev@wazo.community>

ENV DEBIAN_FRONTEND noninteractive

# Add dependencies
RUN apt-get -qq update \
    && apt-get -qqy install \
       libpq-dev \
       libyaml-dev \
    && apt-get -qqy autoremove \
    && apt-get -qq clean \
    && rm -fr /var/lib/apt/lists/*

# Install xivo-call-logd
ADD . /usr/src/xivo-call-logs
WORKDIR /usr/src/xivo-call-logs
RUN pip install -r requirements.txt \
    && python setup.py install \
    && rm -rf /usr/src/xivo-call-logs


# Configure environment
## Certificates
RUN mkdir -p /usr/share/xivo-certs
ADD ./contribs/docker/certs /usr/share/xivo-certs
## Logs
RUN touch /var/log/xivo-call-logd.log
## Config
RUN mkdir -p /etc/xivo-call-logd
ADD ./etc/xivo-call-logd/config.yml /etc/xivo-call-logd/config.yml
## PID
RUN mkdir /var/run/xivo-call-logd

EXPOSE 9298

CMD ["xivo-call-logd", "-fd", "-u", "root"]
