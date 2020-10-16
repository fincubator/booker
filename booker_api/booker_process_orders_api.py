import asyncio
from finteh_proto.utils import get_logger
from booker_api.db.queries import select_orders_to_process, safe_update_order
from finteh_proto.dto import TransactionDTO, OrderDTO

from finteh_proto.enums import OrderType

log = get_logger("OrderProcessing")


def order_from_row(obj) -> OrderDTO:
    """Convert aiopg.sa.RowProxy object (result of select_orders_to_process() module) with Order row data
    to OrderDTO object"""
    in_tx_dto = TransactionDTO(
        coin=obj.in_tx_coin,
        tx_id=obj.in_tx_id,
        to_address=obj.in_tx_to_address,
        from_address=obj.in_tx_from_address,
        amount=obj.in_tx_amount,
        created_at=obj.in_tx_created_at,
        error=obj["in_tx_error"],
        confirmations=obj.in_tx_confirmations,
        max_confirmations=obj.in_tx_max_confirmations,
    )

    out_tx_dto = TransactionDTO(
        coin=obj.out_tx_coin,
        tx_id=obj.out_tx_id,
        to_address=obj.out_tx_to_address,
        from_address=obj.out_tx_from_address,
        amount=obj.out_tx_amount,
        created_at=obj.in_tx_created_at,
        error=obj.out_tx_error,
        confirmations=obj.out_tx_confirmations,
        max_confirmations=obj.out_tx_max_confirmations,
    )

    order_dto = OrderDTO(
        order_id=obj.id, in_tx=in_tx_dto, out_tx=out_tx_dto, order_type=obj.order_type
    )

    return order_dto


class OrdersProcessor:
    def __init__(self, ctx=None):
        self.ctx = ctx

    async def run(self):
        log.info("Start to process orders...")

        while True:
            async with self.ctx.db_engine.acquire() as conn:
                _orders = await select_orders_to_process(conn)

                for row in _orders:

                    order = order_from_row(row)
                    _in_coin = order.in_tx.coin

                    """ If order_type is DEPOSIT, it means that IN transaction
                    was completed in NATIVE (for example Ethereum ERC-20 USDT) blockchain,
                    so TARGET (for example bitshares FINTEH.USDT) blockchain needs to process OUT transaction """
                    if order.order_type == OrderType.DEPOSIT:
                        gw = self.ctx.gateways_clients[_in_coin]["target"]

                    """ If order_type is WITHDRAWAL, it means that IN transaction
                    was completed in TARGET (for example bitshares FINTEH.USDT) blockchain,
                    so NATIVE (for example Ethereum ERC-20 USDT) blockchain
                    needs to process OUT transaction """
                    if row.order_type == OrderType.WITHDRAWAL:
                        gw = self.ctx.gateways_clients[
                            _in_coin.replace(f"{self.ctx.cfg.exchange_prefix}.", "")
                        ]["native"]

                    if not gw:
                        continue

                    if not gw.is_successfully_connected:
                        continue

                    log.info(
                        f"Try {gw} initialize out transaction for {order.order_id}..."
                    )

                    """Gateway must response with TransactionDTO filled max_confirmations and from_address params.
                     It's a signal that gateway ready to execute new transaction
                     """
                    try:
                        # TODO take_fee, remove this mock
                        if order.out_tx.amount == 0 and order.in_tx.amount != 0:
                            order.out_tx.amount = order.in_tx.amount

                        new_tx = await gw.init_new_tx_request(order)

                        assert new_tx.max_confirmations > 0
                        assert new_tx.from_address is not None

                        order.out_tx.max_confirmations = new_tx.max_confirmations
                        order.out_tx.from_address = new_tx.from_address

                        await safe_update_order(conn, order)
                    except Exception as ex:
                        log.info(f"Unable to init new transaction: {new_tx}, {ex}")

            await asyncio.sleep(1)
