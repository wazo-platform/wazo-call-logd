from wazo_call_logd.database.queries.retention import RetentionDAO
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RententionListener:
    dao: RetentionDAO

    def tenant_deleted(self, event: dict):
        tenant_uuid = event['uuid']
        logger.info("cleaning up retention settings for deleted tenant %s", tenant_uuid)
        self.dao.delete(tenant_uuid)
