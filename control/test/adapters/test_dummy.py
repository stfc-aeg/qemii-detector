import sys

import pytest

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock
else:                         # pragma: no cover
    from mock import Mock


class TestDummy():

    def test_fake(self):
        """Test to check that the tox enviroment works on travis"""
        assert True
