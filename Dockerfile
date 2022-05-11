FROM python:3.7-slim-buster AS compile-image
LABEL maintainer="Wazo Maintainers <dev@wazo.community>"

RUN python -m venv /opt/venv
# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"

# Necessary for setproctitle
RUN apt-get -q update
RUN apt-get -yq install gcc

# Install wazo-call-logd requirements
COPY requirements.txt /usr/src/wazo-call-logd/requirements.txt
RUN pip install -r /usr/src/wazo-call-logd/requirements.txt

# Install wazo-call-logd
COPY setup.py /usr/src/wazo-call-logd/setup.py
COPY wazo_call_logd /usr/src/wazo-call-logd/wazo_call_logd
WORKDIR /usr/src/wazo-call-logd
RUN python setup.py install

FROM python:3.7-slim-buster AS build-image
COPY --from=compile-image /opt/venv /opt/venv

COPY ./etc/wazo-call-logd /etc/wazo-call-logd
COPY ./templates /var/lib/wazo-call-logd/templates
RUN true \
    && adduser --quiet --system --group --home /var/lib/wazo-call-logd wazo-call-logd \
    && mkdir -p /etc/wazo-call-logd/conf.d \
    && install -d -o wazo-call-logd -g wazo-call-logd /run/wazo-call-logd/ \
    && install -o wazo-call-logd -g wazo-call-logd /dev/null /var/log/wazo-call-logd.log

EXPOSE 9298

ENV PATH="/opt/venv/bin:$PATH"
CMD ["wazo-call-logd"]
