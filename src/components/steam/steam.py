import logging
import time
from dataclasses import dataclass
from typing import Optional

import gevent
from gevent import Timeout
from gevent.lock import Semaphore

from csgo import sharecode
from csgo.client import CSGOClient
from csgo.proto_enums import GCConnectionStatus
from steam.client import SteamClient
from steam.enums import EResult

from components.steam.constants import SteamLoginStatus
from components.steam.demo import extract_demo_url
from conf.steam import STEAM_GC_TIMEOUT_SEC

logger = logging.getLogger(__name__)


class SteamAPIException(Exception):
    pass


@dataclass
class _Creds:
    username: str
    password: str
    email_code: Optional[str] = None
    two_factor_code: Optional[str] = None


class SteamAPI:
    def __init__(self):
        self.steam_client = SteamClient()
        self.cs_client = CSGOClient(self.steam_client)

        self.steam_loop: Optional[gevent.Greenlet] = None
        self.watchdog_loop: Optional[gevent.Greenlet] = None

        self.connected: bool = False
        self.login_user: Optional[str] = None

        self._gc_lock = Semaphore(1)
        self._last_gc_relaunch_ts = 0.0
        self._last_steam_reconnect_ts = 0.0

        self._creds: Optional[_Creds] = None
        self.needs_email_code: bool = False
        self.needs_2fa_code: bool = False

        self.steam_client.on("disconnected", self._on_disconnected)
        self.steam_client.on("logged_off", self._on_logged_off)

        self.cs_client.on("notready", self._on_gc_notready)
        self.cs_client.on("ready", self._on_gc_ready)


    def connect(self) -> None:
        if self.steam_loop is None or self.steam_loop.dead:
            ok = self.steam_client.connect()
            if not ok:
                raise SteamAPIException("Steam connect failed")
            self.steam_loop = gevent.spawn(self.steam_client.run_forever)

        self.connected = bool(self.steam_client.connected)

        if self.watchdog_loop is None or self.watchdog_loop.dead:
            self.watchdog_loop = gevent.spawn(self._watchdog)

    def disconnect(self) -> None:
        try:
            if self.watchdog_loop and not self.watchdog_loop.dead:
                self.watchdog_loop.kill()
        except Exception:
            logger.exception("SteamAPI[disconnect]: Watchdog kill failed")

        try:
            if self.steam_loop and not self.steam_loop.dead:
                self.steam_loop.kill()
        except Exception:
            logger.exception("SteamAPI[disconnect]: steam loop kill failed")

        try:
            self.steam_client.disconnect()
        except Exception:
            logger.exception("SteamAPI[disconnect]: steam_client.disconnect failed")

        self.connected = False


    def get_cs2_match_url(self, match_code: str) -> Optional[str]:
        self._ensure_connected()

        decoded = sharecode.decode(match_code)
        match_id = int(decoded["matchid"])
        outcome_id = int(decoded["outcomeid"])
        token = int(decoded["token"])

        with self._gc_lock:
            for attempt in (1, 2):
                try:
                    self._ensure_gc_usable()

                    self.cs_client.request_full_match_info(match_id, outcome_id, token)

                    with Timeout(STEAM_GC_TIMEOUT_SEC, SteamAPIException("GC timed out")):
                        ev = self.cs_client.wait_event(
                            "full_match_info",
                            timeout=STEAM_GC_TIMEOUT_SEC,
                            raises=True,
                        )

                    msg = ev[0] if isinstance(ev, (list, tuple)) else ev
                    return extract_demo_url(msg, match_id, token)

                except SteamAPIException:
                    logger.warning("SteamAPI[get_cs2_match_url]: GC timeout. Relaunch and retry (attempt %s)", attempt)
                    self._relaunch_gc(reason="full_match_info_timeout")
                except Exception:
                    logger.exception("SteamAPI[disconnect]: Unexpected error in get_cs2_match_url")
                    return None

        return None

    def login(
        self,
        username: str,
        password: str,
        email_code: Optional[str] = None,
        two_factor_code: Optional[str] = None,
    ) -> tuple[bool, SteamLoginStatus]:
        self._ensure_connected()

        self.needs_email_code = False
        self.needs_2fa_code = False

        res = self.steam_client.login(
            username=username,
            password=password,
            auth_code=email_code,
            two_factor_code=two_factor_code,
        )

        if res == EResult.OK:
            self.login_user = username
            self._creds = _Creds(username, password, email_code, two_factor_code)

            logger.info("SteamAPI[login]: Login OK. Username = %s", username)
            return True, SteamLoginStatus.SUCCESS

        if res == EResult.AccountLogonDenied:
            self.needs_email_code = True
            return False, SteamLoginStatus.EMAIL_CODE_REQUIRED

        if res in (EResult.AccountLoginDeniedNeedTwoFactor, EResult.TwoFactorCodeMismatch):
            self.needs_2fa_code = True
            return False, SteamLoginStatus.TWO_FACTOR_CODE_REQUIRED

        if res == EResult.TryAnotherCM:
            logger.info("SteamAPI[login]: TryAnotherCM received. Trying to reconnect...")
            self.reconnect()

        return False, SteamLoginStatus.FAILED

    def logout(self) -> None:
        self._ensure_connected()
        self.steam_client.logout()
        self.login_user = None
        self._creds = None

    def reconnect(self) -> None:
        self.disconnect()
        self.connect()

    def _ensure_connected(self) -> None:
        if not self.steam_client.connected:
            now = time.time()
            if now - self._last_steam_reconnect_ts < 2.0:
                gevent.sleep(0.2)
            self._last_steam_reconnect_ts = now

            logger.warning("SteamAPI[_ensure_connected]: Steam disconnected, reconnecting...")
            ok = self.steam_client.connect()
            if not ok:
                raise SteamAPIException("SteamAPI[_ensure_connected]: Steam API not connected")

        self.connected = True

        if self.steam_loop is None or self.steam_loop.dead:
            self.steam_loop = gevent.spawn(self.steam_client.run_forever)

    def _auto_relogin(self) -> None:
        try:
            if getattr(self.steam_client, "relogin_available", False):
                logger.warning("SteamAPI[_auto_relogin]: Trying steam_client.relogin()...")
                self.steam_client.relogin()
                return
        except Exception:
            logger.exception("SteamAPI[_auto_relogin]: failed")


        if self._creds:
            logger.warning("SteamAPI[_auto_relogin]: Trying login by password for %s...", self._creds.username)
            res = self.steam_client.login(
                username=self._creds.username,
                password=self._creds.password,
                auth_code=self._creds.email_code,
                two_factor_code=self._creds.two_factor_code,
            )
            logger.warning("SteamAPI[_auto_relogin]: %r", res)

    def _ensure_gc_usable(self, timeout_sec: int = 20) -> None:
        if self.cs_client.connection_status == GCConnectionStatus.HAVE_SESSION:
            return
        self.cs_client.launch()

        end = time.time() + timeout_sec
        while time.time() < end:
            if self.cs_client.connection_status == GCConnectionStatus.HAVE_SESSION:
                return
            gevent.sleep(0.2)

        logger.warning("SteamAPI[_ensure_gc_usable]: GC status still %r after %ss (continue anyway)",
                       self.cs_client.connection_status, timeout_sec)

    def _relaunch_gc(self, reason: str = "") -> None:
        now = time.time()
        if now - self._last_gc_relaunch_ts < 5.0:
            return
        self._last_gc_relaunch_ts = now

        logger.warning("SteamAPI[_relaunch_gc]: Relaunching GC (reason=%s)", reason)
        try:
            self.cs_client.exit()
        except Exception:
            pass
        gevent.sleep(1.5)
        try:
            self.cs_client.launch()
        except Exception:
            pass

    def _watchdog(self) -> None:
        while True:
            try:
                if not self.steam_client.connected:
                    self._ensure_connected()
                    self._auto_relogin()

                if self.cs_client.connection_status != GCConnectionStatus.HAVE_SESSION:
                    if self._gc_lock.acquire(blocking=False):
                        try:
                            self._relaunch_gc(reason=f"watchdog:{self.cs_client.connection_status!r}")
                        finally:
                            self._gc_lock.release()

            except Exception:
                logger.exception("SteamAPI[_watchdog]: watchdog error")

            gevent.sleep(5)


    def _on_disconnected(self, *args, **kwargs):
        logger.warning("SteamAPI[_on_disconnected]: Steam disconnected event")

    def _on_logged_off(self, result=None, *args, **kwargs):
        logger.warning("SteamAPI[_on_logged_off]: Steam logged_off event: %r", result)

    def _on_gc_notready(self, *args, **kwargs):
        logger.warning("SteamAPI[_on_gc_notready]: GC notready event")

    def _on_gc_ready(self, *args, **kwargs):
        logger.info("SteamAPI[_on_gc_ready]: GC ready event")
