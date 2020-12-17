#  Copyright 2020 Soda
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import json
import logging
from typing import List, Optional
from unittest import TestCase

from sodasql.scan.measurement import Measurement
from sodasql.scan.scan import Scan
from sodasql.scan.scan_configuration import ScanConfiguration
from sodasql.sql_store.sql_store import SqlStore
from sodasql.tests.logging_helper import LoggingHelper
from sodasql.tests.measurements import Measurements

LoggingHelper.configure_for_test()


class AbstractScanTest(TestCase):

    def __init__(self, method_name: str = ...) -> None:
        super().__init__(method_name)
        self.sql_store: Optional[SqlStore] = None
        self.connection = None

    def setUp(self) -> None:
        logging.debug(f'\n\n--- {str(self)} ---')
        super().setUp()
        self.sql_store = self.create_sql_store()
        self.connection = self.sql_store.get_connection()

    def tearDown(self) -> None:
        self.connection.rollback()
        self.connection.close()

    def create_sql_store(self) -> SqlStore:
        return SqlStore.create({
            'name': 'test-postgres-store',
            'type': 'postgres',
            'host': 'localhost',
            'port': '5432',
            'username': 'sodalite',
            'database': 'sodalite',
            'schema': 'public'})

    def sql_update(self, sql: str):
        assert self.connection, 'self.connection not initialized'
        with self.connection.cursor() as cursor:
            logging.debug(f'Test SQL update: {sql}')
            return cursor.execute(sql)

    def sql_updates(self, sqls: List[str]):
        for sql in sqls:
            self.sql_update(sql)

    def sql_create_table(self, table_name: str, columns: List[str], rows: List[str]):
        self.sql_updates([
            f"DROP TABLE IF EXISTS {table_name}",

            f"CREATE TABLE {table_name} ( " +
            (", ".join(columns)) +
            f" )",

            f"INSERT INTO {table_name} VALUES " +
            ", ".join(rows)])

    def scan(self, scan_configuration_dict: dict) -> Measurements:
        logging.debug('Scan configuration \n'+json.dumps(scan_configuration_dict, indent=2))
        scan = Scan(self.sql_store, scan_configuration=ScanConfiguration(scan_configuration_dict))
        if len(scan.scan_configuration.parse_logs.logs) > 0:
            raise AssertionError(
                'Scan configuration errors: \n  ' +
                ('\n  '.join([str(log) for log in scan.scan_configuration.parse_logs.logs])))
        return Measurements(scan.execute())
