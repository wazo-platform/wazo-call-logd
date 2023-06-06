import logging
from dataclasses import dataclass

from wazo_call_logd.database.queries.retention import RetentionDAO

logger = logging.getLogger(__name__)


@dataclass
class RetentionListener:
    dao: RetentionDAO

    def tenant_deleted(self, event: dict):
        tenant_uuid = event['uuid']
        logger.info("cleaning up retention settings for deleted tenant %s", tenant_uuid)
        self.dao.delete(tenant_uuid)
