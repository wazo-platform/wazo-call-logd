# wazo-call-logd

[![Build Status](https://jenkins.wazo.community/buildStatus/icon?job=wazo-call-logd)](https://jenkins.wazo.community/job/wazo-call-logd)

wazo-call-logd is a service for collecting statistics on calls made on a Wazo server

## Running unit tests

```shell
tox --recreate -e py39
```

## Developing integration tests

To extract CELs of the latest call from a real Wazo Platform instance and insert
them into an integration test:

```
sudo -u postgres psql asterisk -c "select eventtype,eventtime,channame,uniqueid,linkedid from cel where linkedid = (select max(linkedid) from cel) order by eventtime"
```
