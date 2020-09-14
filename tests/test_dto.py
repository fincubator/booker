import datetime
from finteh_proto.dto import *
from uuid import uuid4
from finteh_proto.utils import object_as_dict


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


def test_dump_tx():
    start_tx = TEST_TX
    dump = start_tx.to_dump()
    assert isinstance(dump, str)

    json_resp = json.loads(dump)
    final_tx = TransactionDTO(**json_resp)
    final_tx = final_tx.normalize()

    assert isinstance(final_tx.amount, Decimal) and isinstance(start_tx.amount, Decimal)
    assert final_tx.amount == start_tx.amount

    assert type(final_tx.created_at) == type(start_tx.created_at) == datetime.datetime
    assert final_tx.created_at == start_tx.created_at

    assert type(final_tx.error) == type(start_tx.error) == TxError
    assert final_tx.error == start_tx.error


def test_dump_order():
    order = OrderDTO(order_id=uuid4(), in_tx=TEST_TX)

    dump = order.to_dump()

    assert isinstance(dump, str)

    json_resp = json.loads(dump)
    in_tx = TransactionDTO(**json_resp["in_tx"]).normalize()
    final_order = OrderDTO(order_id=json_resp["order_id"], in_tx=in_tx)

    assert isinstance(final_order, OrderDTO)
    assert isinstance(final_order.in_tx, TransactionDTO)
    assert final_order.in_tx.amount == TEST_TX.amount


def test_tx_dto_to_model():
    from booker_api.db.models import Tx

    tx_model = Tx(id=uuid4(), **dataclasses.asdict(TEST_TX))
    assert tx_model.error == TEST_TX.error


def test_order_dto_to_model():
    from booker_api.db.models import Tx, Order

    tx_model = Tx(id=uuid4(), **dataclasses.asdict(TEST_TX))
    order_model = Order(id=uuid4(), in_tx=tx_model.id)
    assert order_model.in_tx == tx_model.id


def test_tx_model_to_dto():
    from booker_api.db.models import Tx

    tx_model = Tx(id=uuid4(), **dataclasses.asdict(TEST_TX))
    model_dict = object_as_dict(tx_model)
    model_dict.pop("id")
    new_model = TransactionDTO(**model_dict)
    assert new_model.error == tx_model.error
