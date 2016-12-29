xivo-call-logs
=========
[![Build Status](https://travis-ci.org/wazo-pbx/xivo-call-logs.png?branch=master)](https://travis-ci.org/wazo-pbx/xivo-call-logs)

xivo-call-logs is a service for collecting statistics on calls made on a Wazo server


Running unit tests
------------------

```
apt-get install libpq-dev python-dev libffi-dev libyaml-dev
pip install tox
tox --recreate -e py27
```


