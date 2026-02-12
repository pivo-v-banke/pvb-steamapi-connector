from csgo import sharecode
from starlette.requests import Request

from api_models.cs2 import CS2DemoUrlResponse
from components.steam.steam import SteamAPI


async def get_demo_url_controller(request: Request, match_code: str) -> CS2DemoUrlResponse:

    steam_api: SteamAPI = request.app.state.steam_api
    decoded = sharecode.decode(match_code)
    match_id = int(decoded["matchid"])
    outcome_id = int(decoded["outcomeid"])
    token = int(decoded["token"])

    demo_url = steam_api.get_cs2_match_url(match_code)

    return CS2DemoUrlResponse(
        match_code=match_code,
        match_id=match_id,
        outcome_id=outcome_id,
        token=token,
        demo_url=demo_url,
    )