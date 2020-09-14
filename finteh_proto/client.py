from aiohttp_json_rpc import JsonRpcClient


class BaseClient(JsonRpcClient):
    def __init__(self, ctx=None, host="0.0.0.0", port=8080):
        super().__init__()
        self.ctx = ctx
        self._host = host
        self._port = port

    async def ping(self):
        call_result = await self.call("ping")
        return call_result

    @classmethod
    def safe_call_execute(cls, call):
        async def process_call(client: BaseClient, *args, **kwargs):
            await client.connect(client._host, client._port)
            # TODO Implement Response schema
            try:
                result = await call(client, *args, **kwargs)
            except Exception as ex:
                # TODO Implement Error schema
                result = ex
            await client.disconnect()
            return result

        return process_call

    # TODO Error handle decorator
