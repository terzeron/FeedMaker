#!/usr/bin/env python

from typing import List, Dict, Any, Tuple, Union, Optional
from mysql.connector.pooling import MySQLConnectionPool, PooledMySQLConnection
from mysql.connector.cursor import MySQLCursor


class DBManager:
    def __init__(self, host, port, database, user, password, pool_size=10) -> None:
        self.pool = MySQLConnectionPool(pool_name="mypool", pool_size=pool_size, host=host, port=port, user=user, password=password, database=database)
        self.connection: Optional[PooledMySQLConnection] = None

    def __del__(self):
        del self.pool
        del self.connection

    def get_connection_and_cursor(self) -> Tuple[PooledMySQLConnection, MySQLCursor]:
        connection = self.pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        return connection, cursor

    def query(self, query: str, *params) -> List[Any]:
        connection, cursor = self.get_connection_and_cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        connection.close()
        return result

    def execute(self, cursor: MySQLCursor, query: str, *params) -> None:
        cursor.execute(query, params)

    def commit(self, connection: PooledMySQLConnection, cursor: MySQLCursor) -> None:
        connection.commit()
        cursor.close()
        connection.close()


