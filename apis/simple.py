from fastapi import APIRouter

from exts.logururoute import ContextLogerRoute
from exts.logururoute import async_trace_add_log_record
from exts.responses.json_response import (
    Success,
    Fail,
    ForbiddenException,
    InvalidTokenException,
    BadrequestException,
)

router_simple = APIRouter(
    tags=["简单的API"], prefix="/simple", route_class=ContextLogerRoute
)


@router_simple.get("/index")
async def callback():
    return Success()
