import logging

import gevent
from csgo import sharecode
from csgo.client import CSGOClient
from csgo.proto_enums import GCConnectionStatus
from gevent import Timeout
from steam.client import SteamClient
from steam.enums import EResult

from components.steam.constants import SteamLoginStatus
from components.steam.demo import extract_demo_url
from conf.steam import STEAM_GC_TIMEOUT_SEC

logger = logging.getLogger(__name__)


class SteamAPIException(Exception):
    pass

class SteamAPI:

    def __init__(self):
        self.steam_client = SteamClient()
        self.cs_client = CSGOClient(self.steam_client)
        self.steam_loop = None
        self.connected: bool = False
        self.login_user: str | None = None


    def connect(self) -> None:
        self.steam_client.connect()
        self.steam_loop = gevent.spawn(self.steam_client.run_forever)
        self.connected = True


    def disconnect(self) -> None:
        self.steam_loop.kill()
        self.steam_client.disconnect()
        self.connected = False

    def wait_for_cs(self):
        if self.cs_client.connection_status != GCConnectionStatus.HAVE_SESSION:
            logger.info("SteamAPI[wait_for_cs]: Current CS2 status = %r. Waiting for CS2 launch...", self.cs_client.connection_status)
            self.cs_client.launch()
            logger.info("SteamAPI[wait_for_cs]: CS2 Maybe launched...")
        else:
            logger.info("SteamAPI[wait_for_cs]: CS2 Already launched...")


    def get_cs2_match_url(self, match_code: str) -> str | None:
        self._ensure_connected()
        self.wait_for_cs()

        decoded = sharecode.decode(match_code)
        match_id = int(decoded["matchid"])
        outcome_id = int(decoded["outcomeid"])
        token = int(decoded["token"])

        logger.info(
            "SteamAPI[get_cs2_match_url]: Requesting CS2 match url. Sharecode = %s | match_id = %s | outcome_id = %s | token = %s",
            match_code, match_id, outcome_id, token
        )

        self.cs_client.request_full_match_info(match_id, outcome_id, token)
        with Timeout(STEAM_GC_TIMEOUT_SEC, SteamAPIException("Game coordinator timed out")):
            message = self.cs_client.wait_event("full_match_info", timeout=STEAM_GC_TIMEOUT_SEC, raises=True)

        try:
            cs2_match_url = extract_demo_url(message[0], match_id, token)

            logger.info("SteamAPI[get_cs2_match_url]: Found CS2 match url for sharecode = %s. %s", match_code, cs2_match_url)
            return cs2_match_url

        except Exception as exc:
            logger.exception(exc)
            return None

    def login(
            self,
            username: str,
            password: str,
            email_code: str | None = None,
            two_factor_code: str | None = None,
    ) -> tuple[bool, SteamLoginStatus]:
        self._ensure_connected()

        logger.info("SteamAPI[login]: Logging in with username %s", username)
        steam_result = self.steam_client.login(
            username=username,
            password=password,
            auth_code=email_code,
            two_factor_code=two_factor_code,
        )

        if steam_result == EResult.OK:
            logger.info("SteamAPI[login]: Login successful")
            self.login_user = username
            return True, SteamLoginStatus.SUCCESS

        if steam_result == EResult.AccountLogonDenied:
            logger.info("SteamAPI[login]: Login failed. Email confirmation required")
            return False, SteamLoginStatus.EMAIL_CODE_REQUIRED

        if steam_result in (EResult.AccountLoginDeniedNeedTwoFactor, EResult.TwoFactorCodeMismatch):
            logger.info("SteamAPI[login]: Login failed. 2FA confirmation required")
            return False, SteamLoginStatus.TWO_FACTOR_CODE_REQUIRED

        logger.error("SteamAPI[login]: Login failed. Unknown error. Steam status: %r", steam_result)
        return False, SteamLoginStatus.FAILED

    def logout(self) -> None:
        self._ensure_connected()

        self.steam_client.logout()


    def _ensure_connected(self) -> None:
        self.connected = self.steam_client.connected

        if not self.connected:
            logger.warning("SteamAPI[_ensure_connected]: Steam client disconnected, attempting to reconnect...")
            connected = self.steam_client.connect()
            self.connected = connected
            if not connected:
                raise SteamAPIException("Steam API not connected")


steam_api = SteamAPI()