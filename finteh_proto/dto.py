from decimal import Decimal
from dataclasses import dataclass
import dataclasses
import json
import datetime
from uuid import UUID

from finteh_proto.enums import TxError, OrderType, EnumEncoder, as_enum


@dataclass
class DataTransferClass:
    def __init__(self):
        super().__init__()

    def to_dump(self):
        """Return json-encoded string ready to send with ws-json-rpc. Works recursive for dict objects"""

        # TODO replace this later
        _dict = dataclasses.asdict(self)
        for k, v in _dict.items():
            if k in ("in_tx", "out_tx"):
                if not _dict[k]:
                    continue
                _dict[k]["amount"] = str(_dict[k]["amount"])
                _dict[k]["created_at"] = str(_dict[k]["created_at"])
            if isinstance(v, Decimal):
                _dict[k] = str(v)
            if isinstance(v, datetime.datetime):
                _dict[k] = str(v)
            if isinstance(v, UUID):
                _dict[k] = str(v)

        return json.dumps(_dict, cls=EnumEncoder)


@dataclass
class TransactionDTO(DataTransferClass):
    coin: str
    tx_id: str
    to_address: str
    from_address: str
    amount: Decimal
    created_at: datetime.datetime = datetime.datetime.now()
    error: TxError = TxError.NO_ERROR
    confirmations: int = 0
    max_confirmations: int = 0

    def normalize(self):
        """Cast types after init from json.loads()"""
        self.error = as_enum(self.error)
        self.amount = Decimal(self.amount)
        self.created_at = datetime.datetime.strptime(
            self.created_at, "%Y-%m-%d %H:%M:%S.%f"
        )
        return self


@dataclass
class OrderDTO(DataTransferClass):
    order_id: UUID = None
    in_tx: TransactionDTO = None
    out_tx: TransactionDTO = None
    order_type: OrderType = OrderType.TRASH

    def normalize(self):
        """Cast types after init from json.loads()"""
        self.order_type = as_enum(self.order_type) if self.order_type else None
        self.in_tx = self.in_tx.normalize() if self.in_tx else None
        self.out_tx = self.out_tx.normalize() if self.out_tx else None
        return self


@dataclass
class DepositAddressDTO(DataTransferClass):
    user: str = None
    deposit_address: str = None


@dataclass
class ValidateAddressDTO(DataTransferClass):
    user: str
    is_valid: bool = None


@dataclass
class UpdateTxDTO(DataTransferClass):
    is_updated: bool = False
