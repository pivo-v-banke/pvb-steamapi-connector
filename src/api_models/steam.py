from pydantic import BaseModel

from components.steam.constants import SteamLoginStatus


class SteamLoginRequest(BaseModel):
    username: str
    password: str
    email_code: str | None = None
    two_factor_code: str | None = None


class SteamLoginInfo(BaseModel):
    username: str | None


class SteamLoginResponse(BaseModel):
    success: bool
    status: SteamLoginStatus