test-setup: call-logd docker-pull egg-info

egg-info:
	cd .. && python setup.py egg_info

test:
	nosetests

docker-pull:
	docker pull n3llyb0y/wait
	docker pull p0bailey/docker-flask
	docker pull swaggerapi/swagger-validator
	docker pull wazopbx/postgres-test

call-logd:
	docker build -t wazopbx/xivo-call-logd ..
	docker build --no-cache -t xivo-call-logd-test -f docker/Dockerfile-call-logd-test ..
