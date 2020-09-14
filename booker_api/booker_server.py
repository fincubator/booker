import json
from uuid import uuid4
import dataclasses
import datetime
from aiohttp_json_rpc.protocol import JsonRpcMsg, JsonRpcMsgTyp

from finteh_proto.server import BaseServer
from finteh_proto.dto import TransactionDTO, OrderDTO, UpdateTxDTO
from finteh_proto.enums import OrderType

from booker_api.db.queries import safe_insert_order, update_tx, get_tx_by_tx_id
from booker_api.db.models import Tx, Order
from booker_api.config import Config


class BookerServer(BaseServer):
    def __init__(self, host="0.0.0.0", port=8080, ctx=None):
        super(BookerServer, self).__init__(host, port, ctx)
        self.add_methods(("", self.create_order), ("", self.update_tx))

    async def create_order(self, request):
        """Receiving new (IN) transaction, creating OUT transaction template and Order"""
        in_tx_data = json.loads(request.msg[1]["params"])
        in_tx = TransactionDTO(**in_tx_data).normalize()

        # TODO replace this mock
        out_tx = TransactionDTO(
            amount=in_tx.amount,
            tx_id=None,
            coin=in_tx.coin,
            to_address=in_tx.coin,
            from_address=in_tx.coin,
            confirmations=0,
            max_confirmations=1,
            created_at=datetime.datetime.now(),
        )
        out_tx.tx_id = None

        if self.ctx:
            prefix = self.ctx.cfg.exchange_prefix
        else:
            prefix = Config.exchange_prefix

        if prefix in in_tx.coin:
            order_type = OrderType.WITHDRAWAL
        else:
            order_type = OrderType.DEPOSIT
        order = OrderDTO(
            # TODO remove str()
            order_id=uuid4(),
            in_tx=in_tx,
            out_tx=out_tx,
            order_type=order_type,
        )

        if self.ctx:
            async with self.ctx.db_engine.acquire() as conn:
                in_tx_model = Tx(id=uuid4(), **dataclasses.asdict(in_tx))
                out_tx_model = Tx(id=uuid4(), **dataclasses.asdict(out_tx))
                order_model = Order(
                    id=order.order_id,
                    in_tx=in_tx_model.id,
                    out_tx=out_tx_model.id,
                    order_type=order.order_type,
                )
                await safe_insert_order(conn, in_tx_model, out_tx_model, order_model)

        msg = JsonRpcMsg(type=JsonRpcMsgTyp.RESPONSE, data={"params": order.to_dump()})

        return msg

    async def update_tx(self, request):
        """Update existing transaction"""
        tx_data = json.loads(request.msg[1]["params"])
        tx_dto = TransactionDTO(**tx_data).normalize()

        if self.ctx:
            async with self.ctx.db_engine.acquire() as conn:
                tx_db_data = await get_tx_by_tx_id(conn, tx_dto.tx_id)
                tx_model_instance = Tx(
                    id=tx_db_data["id"], **dataclasses.asdict(tx_dto)
                )
                await update_tx(conn, tx_model_instance)

        updated_order = UpdateTxDTO(is_updated=True)

        msg = JsonRpcMsg(
            type=JsonRpcMsgTyp.RESPONSE, data={"params": updated_order.to_dump()}
        )

        return msg
