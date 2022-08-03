from jaaql.db.db_interface import DBInterface
from psycopg_pool import ConnectionPool
from jaaql.db.db_utils import execute_supplied_statement_singleton
from jaaql.constants import *
from jaaql.db.db_pg_interface import DBPGInterface
import threading

QUERY__fetch_pool_password = "SELECT encrypted_superuser_password FROM jaaql__system WHERE name = :name"
ATTR__encrypted_superuser_password = "encrypted_superuser_password"

PGCONN__max_conns = 5


class DBInterfaceFactory:

    POOLS = {}

    def __init__(self, config: dict, db_crypt_key: bytes, base_url: str = None, base_port: int = None):
        self.config = config
        self.super_connection = None
        self.db_crypt_key = db_crypt_key
        self.base_url = base_url
        self.base_port = None
        self.base_connection_string = "user=%s password=%s dbname=%s"
        if base_url is not None and base_url not in ["127.0.0.1", "localhost"]:
            self.base_connection_string += " host=" + self.base_url
        if base_port is not None and base_port != 5432:
            self.base_connection_string += " port=" + str(self.base_port)
        self.lookup_lock = threading.Lock()

    def set_super_connection(self, super_connection: DBInterface):
        self.set_super_connection(super_connection)

    def init_pool(self, sys_name: str, pool_password: str = None, max_conns: int = None):
        if pool_password is None:
            pool_password = execute_supplied_statement_singleton(self.super_connection, QUERY__fetch_pool_password, {KEY__system_name: sys_name},
                                                                 decrypt_columns=[ATTR__encrypted_superuser_password],
                                                                 encryption_key=self.db_crypt_key)[0][0]
        conn_str = self.base_connection_string % (sys_name, pool_password, sys_name)
        max_conns = PGCONN__max_conns if max_conns is None else max_conns
        DBInterfaceFactory.POOLS = ConnectionPool(conn_str, min_size=max_conns, max_size=max_conns, max_lifetime=60 * 30)

    def fetch_interface(self, sys_name: str, username: str = None, pool_password: str = None, max_conns: int = None):
        if sys_name not in DBInterfaceFactory.POOLS:
            with self.lookup_lock:  # Ideally a parameterised lock but not a thing in Python and too lazy to implement
                if sys_name not in DBInterfaceFactory.POOLS:  # Could have been set before it entered the lock whilst waiting
                    print("Initialising pool for " + sys_name)
                    self.init_pool(sys_name, pool_password, max_conns)

        return DBPGInterface(self.config, DBInterfaceFactory.POOLS[sys_name], sys_name, sys_name if username is None else username)
