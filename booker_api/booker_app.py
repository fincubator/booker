import asyncio
import signal

from aiopg.sa import Engine as DBEngine, create_engine as create_db_engine

from finteh_proto.utils import get_logger

from booker_api.booker_side_client import BookerSideClient
from booker_api.config import Config
from booker_api.booker_process_orders_api import OrdersProcessor
from booker_api.booker_server import BookerServer


log = get_logger("BookerApp")


class AppContext:
    def __init__(self):
        self.cfg = Config()
        self.cfg.with_env()
        self.booker_server = None
        self.db_engine = None
        self.gateways_clients = {}
        self.order_processing: OrdersProcessor

    async def check_connections(self):
        log.info("Run connections checking...")
        while True:
            for coin, clients in self.gateways_clients.items():
                for side in clients:
                    client = clients.get(side)
                    if not client:
                        continue
                    try:
                        await client.connect(
                            client._host, client._port, client.ws_rpc_endpoint
                        )
                        await client.disconnect()
                        if not client.is_successfully_connected:
                            log.info(
                                f"{client} client successfully connected to ws://{client._host}:{client._port}/{client.ws_rpc_endpoint}"
                            )
                        client.is_successfully_connected = True
                    except Exception as ex:
                        if client.is_successfully_connected in (None, True):
                            log.warning(
                                f"{client} client unable to connect ws://{client._host}:{client._port}/{client.ws_rpc_endpoint}: {ex}"
                            )
                        client.is_successfully_connected = False

            await asyncio.sleep(3)

    def run(self):
        loop = asyncio.get_event_loop()
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            loop.add_signal_handler(
                s, lambda sig=s: asyncio.create_task(self.shutdown(loop, signal=s))
            )
        loop.set_exception_handler(self.ex_handler)
        try:
            self.db_engine: DBEngine = loop.run_until_complete(
                create_db_engine(
                    host=self.cfg.db_host,
                    port=self.cfg.db_port,
                    user=self.cfg.db_user,
                    password=self.cfg.db_password,
                    database=self.cfg.db_database,
                )
            )
            log.info(f"Database connected to {self.cfg.db_host}:{self.cfg.db_port}")
        except Exception as ex:
            log.warning(f"Unable to connect database: {ex}")

        self.booker_server = BookerServer(
            ctx=self, host=self.cfg.http_host, port=self.cfg.http_port
        )
        loop.run_until_complete(self.booker_server.start())

        log.info(f"Booker server started on {self.cfg.http_host}:{self.cfg.http_port}")

        for name, data in self.cfg.gateways.items():
            self.gateways_clients[name] = {}
            log.info(f"Setup {name} gateways clients connections...")
            for side, params in data.items():
                if params:
                    gw_client = BookerSideClient(name, side, self, params[0], params[1])
                    self.gateways_clients[name][side] = gw_client
                    log.info(
                        f"{gw_client} created and ready to connect ws://{params[0]}:{params[1]}/ws-rpc"
                    )
                else:
                    log.info(f"{side}{name} client not specified")

        loop.create_task(self.check_connections())

        self.order_processing = OrdersProcessor(self)
        loop.create_task(self.order_processing.run())

        try:
            loop.run_forever()
        finally:
            log.info("Successfully shutdown the app")
            loop.close()

    def ex_handler(self, loop, ex_context):
        ex = ex_context.get("exception")
        coro_name = ex_context["future"].get_coro().__name__

        log.exception(f"{ex.__class__.__name__} in {coro_name}: {ex_context}")

        coro_to_restart = None

        # TODO write to-restart coro parsing logic

        if coro_to_restart:
            log.info(f"Trying to restart {coro_to_restart.__name__} coroutine")
            loop.create_task(coro_to_restart())

    @staticmethod
    async def shutdown(loop, signal=None):
        if signal:
            log.info(f"Received exit signal {signal.name}...")
        else:
            log.info("No exit signal")

        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

        log.info(f"Cancelling {len(tasks)} outstanding tasks")
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        log.info(f"Make some post-shutdown things")
        loop.stop()
