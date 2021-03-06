"""
Test Cases for the QEMII Fem in qemii.detector
Adam Neaves, STFC Detector Systems Software Group
"""

import sys
import pytest

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, MagicMock, call, patch
else:                         # pragma: no cover
    from mock import Mock, MagicMock, call, patch

# sys.modules["qemii.detector.VectorFile"] = Mock()

from qemii.detector.QemFem import QemFem


class FemTestFixture(object):

    def __init__(self):

        self.ip = "127.0.0.1"
        self.port = 8888
        self.id = 0
        with patch("qemii.detector.QemFem.VectorFile"):
            self.fem = QemFem(self.ip, self.port, self.id,
                            self.ip, self.ip, self.ip, self.ip)


@pytest.fixture(scope="class")
def test_fem():
    """Test Fixture for testing the Fem"""

    test_fem = FemTestFixture()
    yield test_fem


class TestFem():

    def test_init(self, test_fem):
        assert test_fem.fem.get_address() == test_fem.ip
