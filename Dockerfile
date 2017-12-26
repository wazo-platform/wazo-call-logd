FROM python:3.5.3
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

# Install wazo-call-logd
ADD . /usr/src/wazo-call-logd
WORKDIR /usr/src/wazo-call-logd
RUN pip install -r requirements.txt \
    && python setup.py install \
    && rm -rf /usr/src/wazo-call-logd


# Configure environment
## Certificates
RUN mkdir -p /usr/share/xivo-certs
ADD ./contribs/docker/certs /usr/share/xivo-certs
## Logs
RUN touch /var/log/wazo-call-logd.log
## Config
RUN mkdir -p /etc/wazo-call-logd
ADD ./etc/wazo-call-logd/config.yml /etc/wazo-call-logd/config.yml
## PID
RUN mkdir /var/run/wazo-call-logd

EXPOSE 9298

CMD ["wazo-call-logd", "-fd", "-u", "root"]
