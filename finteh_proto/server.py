from aiohttp.web import (
    Application,
    TCPSite,
    AppRunner,
    Request as HTTPRequest,
    Response as HTTPResponse,
)
from aiohttp_json_rpc import JsonRpc
from aiohttp_json_rpc.communicaton import JsonRpcRequest


class BaseServer(JsonRpc):
    _host: str
    _port: int
    site: TCPSite
    app: Application
    runner: AppRunner

    def __init__(self, host="0.0.0.0", port=8080, ctx=None):
        super().__init__()
        self.ctx = ctx
        self._host = host
        self._port = port
        self.app = Application()

        self.add_methods(("", self.ping, "", self.test_rpc))

    async def start(self):
        self.app.router.add_route("*", "/", self.handle_request)
        self.app.router.add_route("*", "/status", self.status)
        self.runner = AppRunner(self.app)
        await self.runner.setup()
        self.site = TCPSite(self.runner, self._host, self._port)
        await self.site.start()

    async def stop(self):
        await self.site.stop()

    async def ping(self, request: JsonRpcRequest):
        """WS health check"""
        assert isinstance(request, JsonRpcRequest)
        return "pong"

    async def status(self, request: HTTPRequest) -> HTTPResponse:
        """Http health check"""
        return HTTPResponse(text="Ok")

    async def test_rpc(self, request: JsonRpcRequest):
        return "pong"
