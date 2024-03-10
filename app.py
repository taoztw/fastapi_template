import pathlib
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from exts.exceptions import ApiExceptionHandler
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from config.config import get_settings
from exts.logururoute import ContextLogerRoute
from exts.logururoute.config import setup_ext_loguru
from exts.requestvar import BindContextvarMiddleware
from middlewares.loger.middleware import LogerMiddleware

from apis.user.api import router_user


# APP生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    from db.database import async_engine, Base
    from models.model import ShortUrl, User

    async def init_create_table():
        async with async_engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    await init_create_table()
    setup_ext_loguru(get_settings().BASE_DIR)

    yield


app = FastAPI(
    title="FastAPI Template",
    lifespan=lifespan,
    description="FastAPI Template",
    version="0.0.1",
    debug=True,
)

templates = Jinja2Templates(directory=f"{pathlib.Path.cwd()}/templates/")
staticfiles = StaticFiles(directory=f"{pathlib.Path.cwd()}/static")
app.mount("/static", staticfiles, name="static")


# 本地静态资源
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.png",
    )


# 注册全局异常
ApiExceptionHandler().init_app(app)
# app.router.route_class = ContextLogerRoute
app.add_middleware(
    LogerMiddleware, log_pro_path=os.path.split(os.path.realpath(__file__))[0]
)
app.add_middleware(BindContextvarMiddleware)


# 路由设置
app.include_router(router_user)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app="app:app", host="127.0.0.1", port=8000, reload=True)
