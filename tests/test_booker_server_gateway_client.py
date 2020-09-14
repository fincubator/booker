import datetime
from uuid import uuid4

from booker_api.booker_server import BookerServer

from gateway_api.gateway_side_client import GatewaySideClient

from finteh_proto.dto import *
from finteh_proto.enums import TxError

import pytest


TEST_TX = TransactionDTO(
    amount=Decimal("10.1"),
    tx_id="some:hash",
    coin="USDT",
    to_address="one",
    from_address="two",
    confirmations=0,
    max_confirmations=1,
    created_at=datetime.datetime.now(),
)

TEST_ORDER = OrderDTO(order_id=uuid4(), in_tx=TEST_TX)


@pytest.mark.asyncio
async def test_booker_server_and_gateway_client():
    server = BookerServer()
    await server.start()
    client = GatewaySideClient(port=8888)

    in_tx = TEST_TX

    created_order = await client.create_order_request(in_tx)

    assert isinstance(created_order, OrderDTO)
    assert isinstance(created_order.in_tx, TransactionDTO)
    assert isinstance(created_order.in_tx.error, TxError)
    assert isinstance(created_order.in_tx.amount, Decimal)
    assert created_order.in_tx.amount == TEST_TX.amount

    in_tx.confirmations = 1
    assert in_tx.confirmations == 1

    updated_tx = await client.update_tx_request(TEST_TX)

    assert isinstance(updated_tx, UpdateTxDTO)
    assert updated_tx.is_updated

    await server.stop()
