from utils.base_types import StringEnum


class SteamLoginStatus(StringEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    EMAIL_CODE_REQUIRED = "EMAIL_CODE_REQUIRED"
    TWO_FACTOR_CODE_REQUIRED = "TWO_FACTOR_CODE_REQUIRED"