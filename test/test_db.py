#!/usr/bin/env python


import unittest

from test.test_common import TestCommon
from bin.db import DB
from bin.models import TestTable


class TestDB(unittest.TestCase):
    mysql_container = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mysql_container = TestCommon.prepare_mysql_container()
        DB.init(TestCommon.get_db_config(cls.mysql_container))

    @classmethod
    def tearDownClass(cls) -> None:
        TestCommon.dispose_mysql_container(cls.mysql_container)

    def setUp(self) -> None:
        self.db_config = TestCommon.get_db_config(self.__class__.mysql_container)
        DB.create_all_tables(self.db_config)

    def tearDown(self) -> None:
        DB.drop_all_tables(self.db_config)
        del self.db_config

    def test_insert_and_select(self) -> None:
        with DB.session_ctx(db_config=self.db_config) as s:
            s.add(TestTable(name="Alice", age=10))

        with DB.session_ctx(db_config=self.db_config) as s:
            rows = s.query(TestTable).all()
            assert rows is not None
            self.assertEqual(len(rows), 1)
            for row in rows:
                self.assertEqual(row.name, "Alice")
                self.assertEqual(row.age, 10)

            rows = s.query(TestTable).where(TestTable.name == "Alice").all()
            assert rows is not None
            self.assertEqual(len(rows), 1)
            for row in rows:
                self.assertEqual(row.name, "Alice")
                self.assertEqual(row.age, 10)

    def test_merge_upsert(self) -> None:
        with DB.session_ctx(db_config=self.db_config) as s:
            s.merge(TestTable(name="Alice", age=20))

        with DB.session_ctx(db_config=self.db_config) as s:
            s.merge(TestTable(name="Alice", age=30))

        with DB.session_ctx(db_config=self.db_config) as s:
            rows = s.query(TestTable).where(TestTable.name == "Alice").all()
            assert rows is not None
            for row in rows:
                self.assertEqual(row.age, 30)


if __name__ == "__main__":
    unittest.main()
