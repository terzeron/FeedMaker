#!/usr/bin/env python

import unittest
from unittest.mock import patch, MagicMock

from bin.db import DB
from bin.models import TestTable

class TestDB(unittest.TestCase):
    def setUp(self) -> None:
        # Mock DB config
        self.mock_db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test'
        }
        # Mock DB session
        self.mock_session = MagicMock()
        self.mock_query = MagicMock()
        self.mock_session.query.return_value = self.mock_query
        # Patch DB methods
        self.patcher_init = patch('bin.db.DB.init', return_value=None)
        self.patcher_create = patch('bin.db.DB.create_all_tables', return_value=None)
        self.patcher_drop = patch('bin.db.DB.drop_all_tables', return_value=None)
        self.patcher_session = patch('bin.db.DB.session_ctx')
        self.mock_session_ctx = self.patcher_session.start()
        self.mock_session_ctx.return_value.__enter__.return_value = self.mock_session
        self.mock_session_ctx.return_value.__exit__.return_value = None
        self.patcher_init.start()
        self.patcher_create.start()
        self.patcher_drop.start()
        DB.init(self.mock_db_config)
        DB.create_all_tables(self.mock_db_config)

    def tearDown(self) -> None:
        DB.drop_all_tables(self.mock_db_config)
        self.patcher_init.stop()
        self.patcher_create.stop()
        self.patcher_drop.stop()
        self.patcher_session.stop()
        del self.mock_db_config

    def test_insert_and_select(self) -> None:
        # Mock add and query
        self.mock_session.add.return_value = None
        
        # Create mock row for first query (after insert)
        mock_row1 = MagicMock()
        mock_row1.name = "Alice"
        mock_row1.age = 10
        
        # Create mock row for second query (where clause)
        mock_row2 = MagicMock()
        mock_row2.name = "Alice"
        mock_row2.age = 10
        
        # Track query type
        query_type = []
        
        def all_side_effect(*args, **kwargs):
            if query_type and query_type[-1] == 'where':
                return [mock_row2]
            return [mock_row1]
        
        def where_side_effect(*args, **kwargs):
            query_type.append('where')
            return self.mock_query
        
        self.mock_query.all.side_effect = all_side_effect
        self.mock_query.where.side_effect = where_side_effect
        
        # Insert
        with DB.session_ctx(db_config=self.mock_db_config) as s:
            s.add(TestTable(name="Alice", age=10))
        
        # Select - first query
        with DB.session_ctx(db_config=self.mock_db_config) as s:
            rows = s.query(TestTable).all()
            assert rows is not None
            self.assertEqual(len(rows), 1)
            for row in rows:
                self.assertEqual(row.name, "Alice")
                self.assertEqual(row.age, 10)
        
        # Select - second query (where clause)
        with DB.session_ctx(db_config=self.mock_db_config) as s:
            rows = s.query(TestTable).where(TestTable.name == "Alice").all()
            assert rows is not None
            self.assertEqual(len(rows), 1)
            for row in rows:
                self.assertEqual(row.name, "Alice")
                self.assertEqual(row.age, 10)

    def test_merge_upsert(self) -> None:
        # Mock merge and query
        self.mock_session.merge.return_value = None
        
        # Create mock row for final query (after both merges)
        mock_row = MagicMock()
        mock_row.name = "Alice"
        mock_row.age = 30
        
        # Set up query result
        self.mock_query.all.return_value = [mock_row]
        
        # Upsert
        with DB.session_ctx(db_config=self.mock_db_config) as s:
            s.merge(TestTable(name="Alice", age=20))
        
        with DB.session_ctx(db_config=self.mock_db_config) as s:
            s.merge(TestTable(name="Alice", age=30))
        
        with DB.session_ctx(db_config=self.mock_db_config) as s:
            rows = s.query(TestTable).where(TestTable.name == "Alice").all()
            assert rows is not None
            for row in rows:
                self.assertEqual(row.age, 30)

if __name__ == "__main__":
    unittest.main()
