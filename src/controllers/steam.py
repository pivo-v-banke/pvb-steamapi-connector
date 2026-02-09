from starlette.requests import Request
from starlette.responses import Response

from api_models.steam import SteamLoginRequest, SteamLoginResponse, SteamLoginInfo
from components.steam.steam import steam_api


async def steam_login_controller(payload: SteamLoginRequest) -> SteamLoginResponse:
    success, status = steam_api.login(
        username=payload.username,
        password=payload.password,
        email_code=payload.email_code,
        two_factor_code=payload.two_factor_code,
    )

    return SteamLoginResponse(success=success, status=status)


async def steam_logout_controller() -> Response:
    steam_api.logout()

    return Response(status_code=204)

async def steam_login_info_controller() -> SteamLoginInfo:

    current_username = steam_api.login_user

    return SteamLoginInfo(
        username=current_username,
    )


