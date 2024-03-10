from contextvars import ContextVar
from fastapi import Request
import shortuuid
from starlette.responses import Response, StreamingResponse

from exts.logururoute import setup_ext_loguru
from exts.requestvar.bing import bind_contextvar
from starlette.types import ASGIApp, Receive, Scope, Send
from user_agents import parse
from urllib.parse import parse_qs
from datetime import datetime
from loguru import logger
from utils import json_helper
from typing import Any
import typing
from time import perf_counter

from exts.requestvar import request, request_var


async def async_trace_add_log_record(event_type="", msg: Any = "", remarks=""):
    """

    :param event_type: 日志记录事件描述
    :param msg: 日志记录信息字典
    :param remarks: 日志备注信息
    :return:
    """
    # 如果没有这个标记的属性的，说明这个接口的不需要记录啦！
    if request and hasattr(request.state, "traceid"):
        # 自增编号索引序
        trace_links_index = request.state.trace_links_index = (
            getattr(request.state, "trace_links_index") + 1
        )
        log = {
            # 自定义一个新的参数复制到我们的请求上下文的对象中
            "traceid": getattr(request.state, "traceid"),
            # 定义链路所以序号
            "trace_index": trace_links_index,
            # 时间类型描述描述
            "event_type": event_type,
            # 日志内容详情
            "msg": msg,
            # 日志备注信息
            "remarks": remarks,
        }
        #  为少少相关记录，删除不必要的为空的日志内容信息，
        if not remarks:
            log.pop("remarks")
        if not msg:
            log.pop("msg")
        try:
            log_msg = json_helper.dict_to_json_ensure_ascii(log)  # 返回文本
            logger.info(log_msg)
        except:
            logger.info(
                getattr(request.state, "traceid")
                + "：索引："
                + str(getattr(request.state, "trace_links_index"))
                + ":日志信息写入异常"
            )


class LogerMiddleware:

    def __init__(
        self,
        *,
        app: ASGIApp,
        log_pro_path: str,
        is_record_useragent=False,
        is_record_headers=False,
        nesss_access_heads_keys=[],  # 日志记录需要记录那一部分关键请求头信息
        ignore_url: typing.List = ["/favicon.ico", "websocket"],
    ) -> None:
        self.app = app
        self.is_record_useragent = is_record_useragent
        self.is_record_headers = is_record_headers
        self.nesss_access_heads_keys = nesss_access_heads_keys
        self.ignore_url = ignore_url
        setup_ext_loguru(log_pro_path)

    def make_traceid(self, request) -> None:
        """
        生成追踪链路ID
        :param request:
        :return:
        """
        # 追踪索引序号
        request.state.trace_links_index = 0
        # 追踪ID
        if request.state.traceid:
            pass
        else:
            request.state.traceid = shortuuid.uuid()
        # print(f"LogerMiddleware: {request.state.traceid}")
        # 计算时间
        request.state.start_time = perf_counter()

    def make_token_request(self, request):
        """
        生成当前请求上下文对象request
        :param request:
        :return:
        """
        return request_var.set(request)

    def reset_token_request(self, token_request):
        """
        重置当前请求上下文对象request
        :param request:
        :return:
        """
        request_var.reset(token_request)

    async def get_request_body(self, request) -> typing.AnyStr:
        body = None
        try:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body = await request.json()
                except:
                    pass
                    if body_bytes:
                        try:
                            body = body_bytes.decode("utf-8")
                        except:
                            body = body_bytes.decode("gb2312")
        except:
            pass
        request.state.body = body
        return body

    def filter_request_url(self, request):
        path_info = request.url.path
        # 过滤不需要记录日志请求地址URL
        for item in self.ignore_url:
            if path_info not in item:
                return True
        return False

    async def make_request_log_msg(self, request) -> typing.Dict:
        # 从当前请求中获取到具体的客户端信息
        try:
            ip, method, url = request.client.host, request.method, request.url.path
        except:
            ip, method, url = "", request.method, request.url.path
        # 解析请求提交的表单信息
        try:
            body_form = await request.form()
        except:
            body_form = None
        # 在这里记录下当前提交的body的数据，用于下文的提取
        body = await self.get_request_body(request)
        # 从头部里面获取出对应的请求头信息，用户用户机型等信息获取
        try:
            user_agent = parse(request.headers["user-agent"])
            # 提取UA信息
            browser = user_agent.browser.version
            if len(browser) >= 2:
                browser_major, browser_minor = browser[0], browser[1]
            else:
                browser_major, browser_minor = 0, 0
            # 用户当前系统OS信息提取
            user_os = user_agent.os.version
            if len(user_os) >= 2:
                os_major, os_minor = user_os[0], user_os[1]
            else:
                os_major, os_minor = 0, 0

            log_msg = {
                "headers": (
                    None
                    if not self.is_record_headers
                    else (
                        [
                            request.headers.get(i, "")
                            for i in self.nesss_access_heads_keys
                        ]
                        if self.nesss_access_heads_keys
                        else None
                    )
                ),
                # 记录请求URL信息
                "useragent": (
                    None
                    if not self.is_record_useragent
                    else {
                        "os": "{} {}".format(
                            user_agent.os.family, user_agent.os.version_string
                        ),
                        "browser": "{} {}".format(
                            user_agent.browser.family, user_agent.browser.version_string
                        ),
                        "device": {
                            "family": user_agent.device.family,
                            "brand": user_agent.device.brand,
                            "model": user_agent.device.model,
                        },
                    }
                ),
                "url": url,
                # 记录请求方法
                "method": method,
                # 记录请求来源IP
                "ip": ip,
                # 'path': gziprequest.path,
                # 记录请求提交的参数信息
                "params": {
                    "query_params": parse_qs(str(request.query_params)),
                    "from": body_form,
                    "body": body,
                },
                "ts": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
            }
            # 对于没有的数据清除
            if not log_msg["headers"]:
                log_msg.pop("headers")
            if not log_msg["params"]["query_params"]:
                log_msg["params"].pop("query_params")
            if not log_msg["params"]["from"]:
                log_msg["params"].pop("from")
            if not log_msg["params"]["body"]:
                log_msg["params"].pop("body")
        except:
            log_msg = {
                "headers": (
                    None
                    if not self.is_record_headers
                    else (
                        [
                            request.headers.get(i, "")
                            for i in self.nesss_access_heads_keys
                        ]
                        if self.nesss_access_heads_keys
                        else None
                    )
                ),
                "url": url,
                "method": method,
                "ip": ip,
                "params": {
                    "query_params": parse_qs(str(request.query_params)),
                    "from": body_form,
                    "body": body,
                },
                "ts": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
            }

        # 对于没有的数据清除
        if "headers" in log_msg and not log_msg["headers"]:
            log_msg.pop("headers")
        if log_msg["params"]:
            if (
                "query_params" in log_msg["params"]
                and not log_msg["params"]["query_params"]
            ):
                log_msg["params"].pop("query_params")
            # print(log_msg["params"])
            if "from" in log_msg["params"] and not log_msg["params"]["from"]:
                log_msg["params"].pop("from")
            if "body" in log_msg["params"] and not log_msg["params"]["body"]:
                log_msg["params"].pop("body")

        return log_msg

    def filter_response_context(self, response: Response):
        # 过滤不需要记录日志响应体内容信息L
        return "image" not in response.media_type and hasattr(request.state, "traceid")

    async def after_request_record_loger(self, response: Response):
        if self.filter_response_context(response=response):
            start_time = getattr(request.state, "start_time")
            end_time = f"{(perf_counter() - start_time):.2f}"
            # 获取响应报文信息内容
            rsp = None
            if not isinstance(response, StreamingResponse):
                if isinstance(response, Response):
                    rsp = str(response.body, encoding="utf-8")
                    try:
                        rsp = json_helper.json_to_dict(rsp)
                    except:
                        pass
                log_msg = {
                    # 记录请求耗时
                    "status_code": response.status_code,
                    "cost_time": end_time,
                    #  记录请求响应的最终报文信息--eval的作用是去除相关的 转义符号 "\"ok\""===》ok
                    "rsp": rsp,
                    "ts": f"{datetime.now():%Y-%m-%d %H:%M:%S%z}",
                }
                await async_trace_add_log_record(event_type="response", msg=log_msg)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return

        # 读取一次
        receive_ = await receive()

        # 并定义一个新协程函数的方式返回一个协程
        async def receive():
            return receive_

        # 创建需要解析的参数
        request = Request(scope, receive)

        # 过滤需要记录的请求URL
        if self.filter_request_url(request):
            # 生成链路ID
            self.make_traceid(request)
            # 设置当当前上下文管理对象中
            token_request = self.make_token_request(request)
            # 生成日志记录
            log_msg = await self.make_request_log_msg(request)
            # 开始写日志信息到文件中
            await async_trace_add_log_record(event_type="request", msg=log_msg)
            try:
                response = await self.app(scope, receive, send)
                return response
            finally:
                self.reset_token_request(token_request)
