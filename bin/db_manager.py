#!/usr/bin/env python

from typing import List, Dict, Any
from mysql.connector.pooling import MySQLConnectionPool, PooledMySQLConnection


class DBManager:
    def __init__(self, host, port, database, user, password, pool_size=10) -> None:
        self.pool = MySQLConnectionPool(pool_name="mypool", pool_size=pool_size, host=host, port=port, user=user, password=password, database=database)

    def get_connection(self) -> PooledMySQLConnection:
        return self.pool.get_connection()

    def query(self, query: str, *params) -> List[Dict[str, Any]]:
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        connection.close()
        return result

    def execute(self, query, *params) -> None:
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
        cursor.close()
        connection.close()
