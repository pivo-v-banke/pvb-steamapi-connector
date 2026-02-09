from fastapi import FastAPI

from controllers.cs2 import get_demo_url_controller
from controllers.service import ping_controller
from controllers.steam import steam_login_controller, steam_logout_controller, steam_login_info_controller


def prepare_routes(app: FastAPI) -> None:

    app.add_api_route("/api/ping/", ping_controller, methods=["GET"], tags=["Service"])

    app.add_api_route("/api/steam/login/", steam_login_controller, methods=["POST"], tags=["Steam"])
    app.add_api_route("/api/steam/logout/", steam_logout_controller, methods=["POST"], tags=["Steam"])
    app.add_api_route("/api/steam/login_info/", steam_login_info_controller, methods=["GET"], tags=["Steam"])

    app.add_api_route("/api/cs2/demo/", get_demo_url_controller, methods=["GET"], tags=["CS2"])