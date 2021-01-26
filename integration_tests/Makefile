MANAGE_DB_DIR ?= ../../xivo-manage-db/
POSTGRES_DOCKER=$(MANAGE_DB_DIR)/contribs/docker/wazo-confd-db-test/Dockerfile

test-setup: egg-info call-logd db

egg-info:
	cd .. && python setup.py egg_info

test:
	pytest

call-logd:
	docker build -t wazoplatform/wazo-call-logd ..
	docker build --no-cache -t wazo-call-logd-test -f docker/Dockerfile-call-logd-test ..

update-db:
	docker build --no-cache -t wazoplatform/wazo-confd-db-test -f $(POSTGRES_DOCKER) $(MANAGE_DB_DIR)

db:
	docker build -f ../contribs/docker/Dockerfile-db -t wazoplatform/wazo-call-logd-db ..

.PHONY: test-setup test call-logd update-db db
