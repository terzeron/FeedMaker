#!/usr/bin/env python

from typing import List, Any, Tuple, Optional
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
        del self.pool
        del self.connection

    def get_connection_and_cursor(self, with_serializable_transaction=False) -> Tuple[Connection, Cursor]:
        mysql_connection = self.pool.get_connection()
        connection = Connection(mysql_connection)
        if with_serializable_transaction:
            connection.mysql_connection.start_transaction(isolation_level="SERIALIZABLE")
        cursor = Cursor(mysql_connection.cursor(dictionary=True))
        return connection, cursor

    def query(self, query: str, *params) -> List[Any]:
        connection, cursor = self.get_connection_and_cursor()
        cursor.mysql_cursor.execute(query, params)
        result = cursor.mysql_cursor.fetchall()
        cursor.mysql_cursor.close()
        connection.mysql_connection.close()
        return result

    def execute(self, cursor: Cursor, query: str, *params) -> None:
        cursor.mysql_cursor.execute(query, params)

    def commit(self, connection: Connection, cursor: Cursor) -> None:
        connection.mysql_connection.commit()
        cursor.mysql_cursor.close()
        connection.mysql_connection.close()

    def rollback(self, connection: Connection, cursor: Cursor) -> None:
        connection.mysql_connection.rollback()
        cursor.mysql_cursor.close()
        connection.mysql_connection.close()
