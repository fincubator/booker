import dataclasses
from aiohttp_json_rpc import JsonRpcClient
from aiohttp_json_rpc.exceptions import RpcError

from aiohttp.client_exceptions import ClientConnectorError
from uuid import uuid4
from finteh_proto.dto import JSONRPCResponse, JSONRPCRequest, JSONRPCError
from finteh_proto.utils import get_logger


log = get_logger("JsonRpcClient")


class BaseClient(JsonRpcClient):
    def __init__(self, ctx=None, host="0.0.0.0", port=8080, ws_rpc_endpoint="/ws-rpc"):
        super().__init__()
        self.ctx = ctx
        self._host = host
        self._port = port
        self.ws_rpc_endpoint = ws_rpc_endpoint
        self.is_successfully_connected = None

    async def ping(self):
        """Just RPC string ping-pong"""
        call_result = await self.call("ping")
        return call_result

    @classmethod
    def safe_call_execute(cls, cli_request):
        async def process_call(self: BaseClient, *args, **kwargs) -> JSONRPCResponse:
            try:
                await self.connect(self._host, self._port, self.ws_rpc_endpoint)

                method_name, dto_request, dtc_result = await cli_request(
                    self, *args, **kwargs
                )
                req = JSONRPCRequest(
                    method=method_name,
                    id=uuid4(),
                    params=dto_request.Schema().dump(dto_request),
                )
                req_dump = req.Schema().dump(req)
                log.info(f"Sending request =>> {req}")

                raw_call = await self.call(**req_dump)
                log.info(f"Receiving response <== {raw_call}")

                if "id" in raw_call.keys():
                    """Process response from finteh-proto based WSRPCServer"""
                    response_dto = JSONRPCResponse.Schema().load(raw_call)

                    assert req.id == response_dto.id
                    assert bool(response_dto.error) ^ bool(response_dto.result)

                    if response_dto.error:
                        result = response_dto.error
                    else:
                        result = dtc_result.Schema().load(response_dto.result)

                else:
                    """Process response from other Server"""
                    result = dtc_result.Schema().load(raw_call)

            except ClientConnectorError as ex:

                result = JSONRPCError(
                    code=ex.args[1].errno,
                    message=f"Unable to connect ws server on {self._host}:{self._port}",
                )
            except RpcError as ex:
                result = JSONRPCError(code=ex.error_code, message=ex.message)
            except Exception as ex:
                result = JSONRPCError(code=1, message=str(ex))

            if self._ws:
                await self.disconnect()
            return result

        return process_call
