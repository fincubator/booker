from os import getenv
from pathlib import Path

from dotenv import load_dotenv
import yaml


project_root_dir = Path(__file__).parent.parent


class Config:
    exchange_prefix = "FINTEH"

    db_driver: str = "postgres+psycopg2"
    db_host: str = "0.0.0.0"

    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_database: str = "postgres"

    http_host: str = "0.0.0.0"
    http_port: int = 8080

    gateways: dict = {"USDT": {"native": None, "target": ["0.0.0.0", 6666]}}

    def with_env(self):
        """ Loading local configuration from .env file """
        load_dotenv()
        new_params = dict(
            gateway_prefix=getenv("EXCHANGE_PREFIX"),
            db_driver=getenv("DATABASE_DRIVER"),
            db_host=getenv("DATABASE_HOST"),
            db_port=getenv("DATABASE_PORT"),
            db_user=getenv("DATABASE_USERNAME"),
            db_password=getenv("DATABASE_PASSWORD"),
            db_database=getenv("DATABASE_NAME"),
            http_host=getenv("HTTP_HOST"),
            http_port=getenv("HTTP_PORT"),
        )

        for name, value in new_params.items():
            if not value:
                print(f"bad value for {name}: {value}")
                raise AttributeError

            setattr(self, name, value)

        """ Loading remote gateways configurations from gateways.yml file """
        self.gateways = yaml.safe_load(open(f"{project_root_dir}/gateways.yml", "r"))
