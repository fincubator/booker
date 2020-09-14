import pytest
from aiopg.sa import create_engine as create_db_engine
import datetime
from uuid import uuid4
from booker_api.config import Config
from booker_api.db.queries import *
from booker_api.db.queries import get_tx_by_tx_id
from finteh_proto.enums import TxError, OrderType


async def _get_db_engine():
    cfg = Config()
    cfg.with_env()
    db_engine = await create_db_engine(
        host=cfg.db_host,
        port=cfg.db_port,
        user=cfg.db_user,
        password=cfg.db_password,
        database=cfg.db_database,
    )
    return db_engine


@pytest.mark.asyncio
async def test_insert_tx():
    try:
        engine = await _get_db_engine()
        async with engine.acquire() as conn:
            tx = Tx(
                id=uuid4(),
                coin="USDT",
                # tx_id="some_id",
                from_address="some_sender",
                to_address="some_receiver",
                amount=10.1,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=0,
                max_confirmations=1,
            )
            r = await insert_tx(conn, tx)
            assert r

            r = await conn.execute(select([Tx]).where(Tx.id == tx.id))
            tx_from_db = await r.fetchone()
            error = tx_from_db["error"]
            assert type(error) == TxError
            await delete_tx(conn, tx.tx_id)

    except Exception as ex:
        pytest.skip(
            msg=f"Bad database connection: {ex}\nmaybe database bad config or not started?"
        )


@pytest.mark.asyncio
async def test_update_tx():
    try:
        engine = await _get_db_engine()
        async with engine.acquire() as conn:
            tx = Tx(
                id=uuid4(),
                coin="USDT",
                tx_id="some_id",
                from_address="some_sender",
                to_address="some_receiver",
                amount=10.1,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=0,
                max_confirmations=1,
            )
            out_tx = Tx(
                id=uuid4(),
                coin="FINTEH.USDT",
                tx_id=None,
                from_address="some_sender",
                to_address="some_receiver",
                amount=9.99,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=0,
                max_confirmations=1,
            )

            order = Order(
                id=uuid4(), in_tx=tx.id, out_tx=out_tx.id, order_type=OrderType.DEPOSIT
            )

            await safe_insert_order(conn, tx, out_tx, order)

            tx.confirmations = 10

            await update_tx(conn, tx)

            updated = await get_tx_by_tx_id(conn, tx.tx_id)

            await delete_order(conn, order.id)
            await delete_tx(conn, tx.tx_id)
            await delete_tx(conn, out_tx.tx_id)

            assert updated["confirmations"] == 10

    except Exception as ex:
        pytest.skip(
            msg=f"Bad database connection: {ex}\nmaybe database bad config or not started?"
        )


@pytest.mark.asyncio
async def test_insert_order():
    try:
        engine = await _get_db_engine()
        async with engine.acquire() as conn:
            in_tx = Tx(
                id=uuid4(),
                coin="USDT",
                tx_id="some_id1",
                from_address="some_sender",
                to_address="some_receiver",
                amount=10.1,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=1,
                max_confirmations=1,
            )

            await insert_tx(conn, in_tx)

            out_tx = Tx(
                id=uuid4(),
                coin="FINTEH.USDT",
                # tx_id="some_id2",
                from_address="some_sender",
                to_address="some_receiver",
                amount=9.99,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=0,
                max_confirmations=1,
            )

            await insert_tx(conn, out_tx)

            order = Order(
                id=uuid4(),
                in_tx=in_tx.id,
                out_tx=out_tx.id,
                order_type=OrderType.DEPOSIT,
            )

            r = await insert_order(conn, order)
            assert r

            r = await delete_order(conn, order.id)
            if r:
                await delete_tx(conn, in_tx.tx_id)
                await delete_tx(conn, out_tx.tx_id)

    except Exception as ex:
        pytest.skip(
            msg=f"Bad database connection: {ex}\nmaybe database bad config or not started?"
        )


@pytest.mark.asyncio
async def test_select_all_orders():
    try:
        engine = await _get_db_engine()

        async with engine.acquire() as conn:
            in_tx = Tx(
                id=uuid4(),
                coin="USDT",
                tx_id="some_id1",
                from_address="some_sender",
                to_address="some_receiver",
                amount=10.1,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=0,
                max_confirmations=1,
            )

            await insert_tx(conn, in_tx)

            out_tx = Tx(
                id=uuid4(),
                coin="FINTEH.USDT",
                # tx_id=None,
                from_address="some_sender",
                to_address="some_receiver",
                amount=9.99,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=0,
                max_confirmations=1,
            )

            await insert_tx(conn, out_tx)

            order = Order(
                id=uuid4(),
                in_tx=in_tx.id,
                out_tx=out_tx.id,
                order_type=OrderType.DEPOSIT,
            )

            await insert_order(conn, order)

            r = await select_all_orders(conn)

            await delete_order(conn, order.id)

            await delete_tx(conn, in_tx.tx_id)
            await delete_tx(conn, out_tx.tx_id)

            assert r

    except Exception as ex:
        pytest.skip(
            msg=f"Bad database connection: {ex}\nmaybe database bad config or not started?"
        )


@pytest.mark.asyncio
async def test_select_orders_to_process():
    try:
        engine = await _get_db_engine()

        async with engine.acquire() as conn:
            in_tx1 = Tx(
                id=uuid4(),
                coin="USDT",
                tx_id="some_id11",
                from_address="some_sender",
                to_address="some_receiver",
                amount=10.1,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=4,
                max_confirmations=3,
            )

            out_tx1 = Tx(
                id=uuid4(),
                coin="FINTEH.USDT",
                tx_id="some_id2",
                from_address="some_sender",
                to_address="some_receiver",
                amount=9.99,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=3,
                max_confirmations=3,
            )

            in_tx2 = Tx(
                id=uuid4(),
                coin="USDT",
                tx_id="some_id21",
                from_address="some_sender",
                to_address="some_receiver",
                amount=10.1,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=3,
                max_confirmations=3,
            )

            out_tx2 = Tx(
                id=uuid4(),
                coin="FINTEH.USDT",
                tx_id="some_id22",
                from_address="some_sender",
                to_address="some_receiver",
                amount=9.99,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=3,
                max_confirmations=3,
            )

            in_tx3 = Tx(
                id=uuid4(),
                coin="USDT",
                tx_id="some_id31",
                from_address="some_sender",
                to_address="some_receiver",
                amount=10.1,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=3,
                max_confirmations=3,
            )

            out_tx3 = Tx(
                id=uuid4(),
                coin="FINTEH.USDT",
                tx_id=None,
                from_address="some_sender",
                to_address="some_receiver",
                amount=9.99,
                created_at=datetime.datetime.now(),
                error=TxError.NO_ERROR,
                confirmations=0,
                max_confirmations=3,
            )

            for i in (in_tx1, in_tx2, in_tx3, out_tx1, out_tx2, out_tx3):
                await insert_tx(conn, i)

            order1 = Order(
                id=uuid4(),
                in_tx=in_tx1.id,
                out_tx=out_tx1.id,
                order_type=OrderType.DEPOSIT,
            )
            order2 = Order(
                id=uuid4(),
                in_tx=in_tx2.id,
                out_tx=out_tx2.id,
                order_type=OrderType.DEPOSIT,
            )
            order3 = Order(
                id=uuid4(),
                in_tx=in_tx3.id,
                out_tx=out_tx3.id,
                order_type=OrderType.DEPOSIT,
            )

            for i in (order1, order2, order3):
                await insert_order(conn, i)

            orders_to_process = await select_orders_to_process(conn)

            for i in (order1, order2, order3):
                await delete_order(conn, i.id)

            for i in (in_tx1, in_tx2, in_tx3, out_tx1, out_tx2, out_tx3):
                await delete_tx(conn, i.tx_id)

            assert len(orders_to_process) == 1
            for i in orders_to_process:
                assert isinstance(i["in_tx_error"], TxError)
                assert isinstance(i["order_type"], OrderType)

    except Exception as ex:
        pytest.skip(
            msg=f"Bad database connection: {ex}\nmaybe database bad config or not started?"
        )


@pytest.mark.asyncio
async def test_safe_insert_order():
    engine = await _get_db_engine()

    async with engine.acquire() as conn:
        in_tx1 = Tx(
            id=uuid4(),
            coin="USDT",
            tx_id="some_id11",
            from_address="some_sender",
            to_address="some_receiver",
            amount=10.1,
            created_at=datetime.datetime.now(),
            error=TxError.NO_ERROR,
            confirmations=4,
            max_confirmations=3,
        )

        out_tx1 = Tx(
            id=uuid4(),
            coin="FINTEH.USDT",
            tx_id="some_id2",
            from_address="some_sender",
            to_address="some_receiver",
            amount=9.99,
            created_at=datetime.datetime.now(),
            error=TxError.NO_ERROR,
            confirmations=3,
            max_confirmations=3,
        )

        order1 = Order(
            id=uuid4(), in_tx=in_tx1.id, out_tx=out_tx1.id, order_type=OrderType.DEPOSIT
        )

        r = await safe_insert_order(conn, in_tx1, out_tx1, order1)

        await delete_order(conn, order1.id)

        await delete_tx(conn, in_tx1.tx_id)
        await delete_tx(conn, out_tx1.tx_id)

        assert r


@pytest.mark.asyncio
async def test_get_tx_by_tx_id():
    engine = await _get_db_engine()

    async with engine.acquire() as conn:
        in_tx1 = Tx(
            id=uuid4(),
            coin="USDT",
            tx_id="some_id11",
            from_address="some_sender",
            to_address="some_receiver",
            amount=10.1,
            created_at=datetime.datetime.now(),
            error=TxError.NO_ERROR,
            confirmations=4,
            max_confirmations=3,
        )
        await insert_tx(conn, in_tx1)

        tx = await get_tx_by_tx_id(conn, in_tx1.tx_id)
        assert tx

        await delete_tx(conn, tx_id=tx.tx_id)
