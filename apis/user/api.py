from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from dependencies import get_db_session
from db.database import AsyncSession
from apis.user.service import UserServeries
from starlette.status import HTTP_401_UNAUTHORIZED
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta, datetime


from exts.logururoute import async_trace_add_log_record, ContextLogerRoute
from exts.requestvar import request
from utils.passlib_hepler import PasslibHelper
from utils.auth_helper import AuthToeknHelper
from utils.random_helper import generate_short_url
from fastapi import File, UploadFile

from exts.responses.json_response import (
    Success,
    Fail,
    ForbiddenException,
    InvalidTokenException,
    BadrequestException,
)


router_user = APIRouter(
    prefix="/api/v1", tags=["用户管理"], route_class=ContextLogerRoute
)
# 注意需要请求的是完整的路径
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/apis/v1/oauth2/authorize")


@router_user.post("/oauth2/authorize", summary="请求授权URL地址")
async def login(
    user_data: OAuth2PasswordRequestForm = Depends(),
    db_session: AsyncSession = Depends(get_db_session),
):
    if not user_data:
        # raise HTTPException(status_code=400, detail="请输入用户账号及密码等信息")
        return BadrequestException()
    # 查询用户是否存在
    userinfo = await UserServeries.get_user_by_name(db_session, user_data.username)
    if not userinfo:
        # raise HTTPException(
        #     status_code=HTTP_401_UNAUTHORIZED,
        #     detail="不存在此用户信息",
        #     headers={"WWW-Authenticate": "Basic"},
        # )
        return InvalidTokenException()

    # 验证用户密码和哈希密码值是否保持一直
    if not PasslibHelper.verity_password(user_data.password, userinfo.password):
        return ForbiddenException()

    # 签发JWT有效负载信息
    data = {
        "iss ": userinfo.username,  # 签发者
        "sub": "xiaozhongtongxue",  # 主题
        "username": userinfo.username,
        "admin": True,  # 是否是管理员
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    # 生成Token
    token = AuthToeknHelper.token_encode(data=data)
    await async_trace_add_log_record(event_type="third", msg="用户登录成功！")
    return Success(result={"access_token": token, "token_type": "bearer"})
