from xivo.rest_api_helpers import APIException


class CDRNotFoundException(APIException):
    def __init__(self, details=None):
        super(CDRNotFoundException, self).__init__(
            status_code=404,
            message='No CDR found matching this ID',
            error_id='cdr-not-found-with-given-id',
            details=details,
        )
