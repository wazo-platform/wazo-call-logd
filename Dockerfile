FROM python:3.7-slim-buster AS compile-image
LABEL maintainer="Wazo Maintainers <dev@wazo.community>"

RUN python -m venv /opt/venv
# Activate virtual env
ENV PATH="/opt/venv/bin:$PATH"

# Install wazo-call-logd
COPY . /usr/src/wazo-call-logd
WORKDIR /usr/src/wazo-call-logd
RUN pip install -r requirements.txt
RUN python setup.py install

FROM python:3.7-slim-buster AS build-image
COPY --from=compile-image /opt/venv /opt/venv

COPY ./etc/wazo-call-logd /etc/
RUN true \
    && adduser --quiet --system --group --home /var/lib/wazo-call-logd wazo-call-logd \
    && mkdir -p /etc/wazo-call-logd/conf.d \
    && install -d -o wazo-call-logd -g wazo-call-logd /run/wazo-call-logd/ \
    && install -o wazo-call-logd -g wazo-call-logd /dev/null /var/log/wazo-call-logd.log

EXPOSE 9298

ENV PATH="/opt/venv/bin:$PATH"
CMD ["wazo-call-logd", "-d", "-u", "root"]
