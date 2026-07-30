ifeq ($(MANAGE_DB_DIR),)
	CEL_DB_TARGET=cel-db-pull
else
	CEL_DB_TARGET=cel-db-build
	CEL_POSTGRES_DOCKER=$(MANAGE_DB_DIR)/contribs/docker/wazo-confd-db-test/Dockerfile
endif

test-setup: egg-info call-logd purge-db db cel-db

egg-info:
	cd .. && python setup.py egg_info

test:
	pytest

purge-db:
	docker build --no-cache -t wazo-purge-db-test -f docker/Dockerfile-purge-db-test ..

call-logd:
	docker build --no-cache -t wazoplatform/wazo-call-logd ..
	docker build --no-cache -t wazo-call-logd-test -f docker/Dockerfile-call-logd-test ..

cel-db: $(CEL_DB_TARGET)

cel-db-pull:
	docker pull wazoplatform/wazo-confd-db-test
	docker tag wazoplatform/wazo-confd-db-test:latest wazoplatform/wazo-confd-db-test:local

cel-db-build:
	docker build --pull --no-cache -t wazoplatform/wazo-confd-db-test:local -f $(CEL_POSTGRES_DOCKER) $(MANAGE_DB_DIR)

db:
	docker build -f ../contribs/docker/Dockerfile-db -t wazoplatform/wazo-call-logd-db ..

.PHONY: test-setup test call-logd purge-db cel-db cel-db-pull cel-db-build db
