MANAGE_DB_DIR ?= ../../xivo-manage-db/
POSTGRES_DOCKER=$(MANAGE_DB_DIR)/contribs/postgres-test/Dockerfile

test-setup: call-logd egg-info

egg-info:
	cd .. && python setup.py egg_info

test:
	pytest

call-logd:
	docker build -t wazopbx/wazo-call-logd ..
	docker build --no-cache -t wazo-call-logd-test -f docker/Dockerfile-call-logd-test ..

update-db:
	docker build --no-cache -t wazopbx/postgres-test -f $(POSTGRES_DOCKER) $(MANAGE_DB_DIR)

.PHONY: test-setup test call-logd update-db
