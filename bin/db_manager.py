#!/usr/bin/env python

from typing import List, Any, Tuple, Optional
from contextlib import contextmanager
from mysql.connector.pooling import MySQLConnectionPool, PooledMySQLConnection
from mysql.connector.cursor import MySQLCursor
import mysql.connector

IntegrityError = mysql.connector.errors.IntegrityError


class Connection:
    def __init__(self, connection: PooledMySQLConnection):
        self.mysql_connection: PooledMySQLConnection = connection

    def __del__(self):
        del self.mysql_connection


class Cursor:
    def __init__(self, cursor: MySQLCursor):
        self.mysql_cursor: MySQLCursor = cursor

    def __del__(self):
        del self.mysql_cursor


class DBManager:
    def __init__(self, host, port, database, user, password, pool_size=10) -> None:
        self.pool = MySQLConnectionPool(pool_name="mypool", pool_size=pool_size, host=host, port=port, user=user, password=password, database=database)
        self.connection: Optional[PooledMySQLConnection] = None

    def __del__(self):
        if self.pool:
            del self.pool
        if self.connection:
            self.connection.close()
            del self.connection

    @contextmanager
    def get_connection_and_cursor(self, with_serializable_transaction=False) -> Tuple[Connection, Cursor]:
        mysql_connection = self.pool.get_connection()
        connection = Connection(mysql_connection)
        if with_serializable_transaction:
            connection.mysql_connection.start_transaction(isolation_level="SERIALIZABLE")
        cursor = Cursor(mysql_connection.cursor(dictionary=True))
        try:
            yield connection, cursor
        finally:
            cursor.mysql_cursor.close()
            connection.mysql_connection.close()

    def query(self, query: str, *params) -> List[Any]:
        with self.get_connection_and_cursor() as (connection, cursor):
            cursor.mysql_cursor.execute(query, params)
            result = cursor.mysql_cursor.fetchall()
            return result

    def execute(self, cursor: Cursor, query: str, *params) -> None:
        cursor.mysql_cursor.execute(query, params)

    def commit(self, connection: Connection) -> None:
        connection.mysql_connection.commit()

    def rollback(self, connection: Connection) -> None:
        connection.mysql_connection.rollback()
