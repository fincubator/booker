import pytest
import aiohttp

from finteh_proto.server import BaseServer
from finteh_proto.client import BaseClient


@pytest.mark.asyncio
async def test_base_ping_pong():
    server = BaseServer()
    await server.start()

    client = BaseClient()
    await client.connect("0.0.0.0", 8080)

    call_result = await client.ping()
    assert call_result == "pong"

    await client.disconnect()
    await server.stop()


@pytest.mark.asyncio
async def test_base_status():
    server = BaseServer()
    await server.start()

    r = await aiohttp.ClientSession().get("http://0.0.0.0:8080/status")
    assert r.status == 200
    assert await r.text() == "Ok"

    await server.stop()


@pytest.mark.asyncio
async def test_dto_by_rpc():
    import dataclasses

    from marshmallow_dataclass import dataclass
    from finteh_proto.dto import DataTransferClass

    @dataclass
    class TestDTO(DataTransferClass):
        int_param: int
        str_param: str
        bool_param: bool

    t_obj = TestDTO(int_param=1, str_param="HW", bool_param=True)

    server = BaseServer()
    await server.start()

    client = BaseClient()
    await client.connect("0.0.0.0", 8080)

    call_result = await client.call("test_rpc", t_obj)
    assert call_result == "pong"

    await client.disconnect()
    await server.stop()
