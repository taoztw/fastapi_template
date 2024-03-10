from functools import lru_cache
from pydantic import ConfigDict
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 定义连接异步引擎数据库的URL地址
    ASYNC_DATABASE_URI: str = (
        "sqlite+aiosqlite:////Users/tz/PycharmProjects/fastapi_learn_projects/short_url_pro/short.db"
    )
    # 定义TOEKN的签名信息值
    TOKEN_SIGN_SECRET: str = "ZcjT6Rcp1yIFQoS7"

    LOG_DIR: str = os.path.dirname(os.path.dirname(__file__))
    BASE_DIR: str = os.path.dirname(os.path.dirname(__file__))


@lru_cache()
def get_settings():
    return Settings()
