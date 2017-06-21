wazo-call-logd
=========
[![Build Status](https://travis-ci.org/wazo-pbx/wazo-call-logd.png?branch=master)](https://travis-ci.org/wazo-pbx/wazo-call-logd)

wazo-call-logd is a service for collecting statistics on calls made on a Wazo server


Running unit tests
------------------

```
apt-get install libpq-dev python3.4-dev libffi-dev libyaml-dev
pip install tox
tox --recreate -e py34
```
