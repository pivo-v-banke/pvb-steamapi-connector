from starlette.requests import Request
from starlette.responses import Response

from api_models.steam import SteamLoginRequest, SteamLoginResponse, SteamLoginInfo
from components.steam.steam import SteamAPI


async def steam_login_controller(request: Request, payload: SteamLoginRequest) -> SteamLoginResponse:
    steam_api: SteamAPI = request.app.state.steam_api
    success, status = steam_api.login(
        username=payload.username,
        password=payload.password,
        email_code=payload.email_code,
        two_factor_code=payload.two_factor_code,
    )

    return SteamLoginResponse(success=success, status=status)


async def steam_logout_controller(request: Request) -> Response:
    steam_api: SteamAPI = request.app.state.steam_api
    steam_api.logout()

    return Response(status_code=204)

async def steam_login_info_controller(request: Request) -> SteamLoginInfo:
    steam_api: SteamAPI = request.app.state.steam_api

    current_username = steam_api.login_user

    return SteamLoginInfo(
        username=current_username,
    )


