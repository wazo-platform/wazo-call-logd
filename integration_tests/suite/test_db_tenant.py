# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import uuid

from hamcrest import (
    assert_that,
    equal_to,
    has_items,
    has_properties,
)

from wazo_call_logd.database.models import Tenant

from .helpers.base import DBIntegrationTest


class TestTenant(DBIntegrationTest):
    def test_create_all_empty(self):
        before_create = self.session.query(Tenant).all()

        tenant_uuids = []
        self.dao.tenant.create_all_uuids_if_not_exist(tenant_uuids)

        after_create = self.session.query(Tenant).all()
        assert_that(len(after_create), equal_to(len(before_create)))

    def test_create_all(self):
        tenant1 = uuid.uuid4()
        tenant2 = uuid.uuid4()

        tenant_uuids = [tenant1, tenant2]
        self.dao.tenant.create_all_uuids_if_not_exist(tenant_uuids)

        result = self.session.query(Tenant).all()
        assert_that(
            result,
            has_items(
                has_properties(uuid=tenant1),
                has_properties(uuid=tenant2),
            ),
        )

        query = self.session.query(Tenant).filter(Tenant.uuid.in_(tenant_uuids))
        query.delete(synchronize_session=False)
        self.session.commit()

    def test_create_all_when_exist(self):
        tenant_uuid_1 = uuid.uuid4()
        self.dao.tenant.create_all_uuids_if_not_exist([str(tenant_uuid_1)])
        tenant_uuid_2 = uuid.uuid4()

        tenant_uuids = [str(tenant_uuid_1), str(tenant_uuid_2)]
        self.dao.tenant.create_all_uuids_if_not_exist(tenant_uuids)

        result = self.session.query(Tenant).all()
        assert_that(
            result,
            has_items(
                has_properties(uuid=tenant_uuid_1),
                has_properties(uuid=tenant_uuid_2),
            ),
        )

        query = self.session.query(Tenant).filter(Tenant.uuid.in_(tenant_uuids))
        query.delete(synchronize_session=False)
        self.session.commit()
