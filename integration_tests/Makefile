MANAGE_DB_DIR ?= ../../xivo-manage-db/
CEL_POSTGRES_DOCKER=$(MANAGE_DB_DIR)/contribs/docker/wazo-confd-db-test/Dockerfile

test-setup: egg-info call-logd purge-db db

egg-info:
	cd .. && python setup.py egg_info

test:
	pytest

purge-db:
	docker build --no-cache -t wazo-purge-db-test -f docker/Dockerfile-purge-db-test ..

call-logd:
	docker build -t wazoplatform/wazo-call-logd ..
	docker build --no-cache -t wazo-call-logd-test -f docker/Dockerfile-call-logd-test ..

cel-db:
	sed -i 's|wazoplatform/wazo-confd-db|wazoplatform/wazo-confd-db:bullseye|' $(CEL_POSTGRES_DOCKER)
	docker build --no-cache -t wazoplatform/wazo-confd-db-test -f $(CEL_POSTGRES_DOCKER) $(MANAGE_DB_DIR)
	sed -i 's|wazoplatform/wazo-confd-db:bullseye|wazoplatform/wazo-confd-db|' $(CEL_POSTGRES_DOCKER)

db:
	docker build -f ../contribs/docker/Dockerfile-db -t wazoplatform/wazo-call-logd-db ..

.PHONY: test-setup test call-logd purge-db cel-db db
