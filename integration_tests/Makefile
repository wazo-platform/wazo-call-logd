MANAGE_DB_DIR ?= ../../manage-db/
POSTGRES_DOCKER=$(MANAGE_DB_DIR)/contribs/postgres-test/Dockerfile

test-setup: call-logd docker-pull egg-info

egg-info:
	cd .. && python setup.py egg_info

test:
	nosetests

docker-pull:
	docker pull p0bailey/docker-flask
	docker pull swaggerapi/swagger-validator
	docker pull wazopbx/wait
	docker pull wazopbx/postgres
	docker pull wazopbx/postgres-test
	docker pull wazopbx/wazo-auth-mock
	docker pull wazopbx/xivo-confd-mock

call-logd:
	docker build --pull -t wazopbx/wazo-call-logd ..
	docker build --no-cache -t wazo-call-logd-test -f docker/Dockerfile-call-logd-test ..

update-db:
	docker build --no-cache -t wazopbx/postgres-test -f $(POSTGRES_DOCKER) $(MANAGE_DB_DIR)
