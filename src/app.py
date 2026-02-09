from contextlib import asynccontextmanager
from logging.config import dictConfig

from fastapi import FastAPI

from conf.logging import LOGGING_CONFIG
from conf.secret import API_SECRET_KEY, API_SECRET_KEY_REQUIRED
from middlewares import APIKeyMiddleware, ExceptionMiddleware
from routes import prepare_routes

from components.steam.steam import SteamAPI, SteamAPIException, steam_api


def prepare_app() -> FastAPI:
    dictConfig(LOGGING_CONFIG)

    fastapi_app = FastAPI()
    steam_api.connect()

    fastapi_app.add_middleware(
        APIKeyMiddleware,
        api_key=API_SECRET_KEY,
        api_key_required=API_SECRET_KEY_REQUIRED,
    )
    fastapi_app.add_middleware(
        ExceptionMiddleware,
        exc_class=SteamAPIException,
    )
    fastapi_app.add_middleware(
        ExceptionMiddleware,
        exc_class=ValueError,
        status_code=400,
    )

    prepare_routes(fastapi_app)
    return fastapi_app


app = prepare_app()