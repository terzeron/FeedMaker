#!/usr/bin/env python

# mypy: disable-error-code="import"

import logging
import logging.config
from pathlib import Path
from typing import Dict, Any


# Configure logging for tests
logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class CommonTestUtil:
    """Common test utilities for feed maker tests"""
    
    @staticmethod
    def get_test_config() -> Dict[str, Any]:
        """Get test configuration"""
        return {
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test'
        }
    
    @staticmethod
    def get_test_loki_url() -> str:
        """Get test Loki URL"""
        return "http://localhost:3100"
