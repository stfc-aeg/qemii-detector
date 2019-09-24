"""
Test Cases for the QEMII RdmaUDP in qemii.detector
Adam Neaves, STFC Detector Systems Software Group
"""

import sys
import pytest

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, MagicMock, call, patch
else:                         # pragma: no cover
    from mock import Mock, MagicMock, call, patch

from qemii.detector.RdmaUDP import RdmaUDP


class RdmaUDPTestFixture(object):

    def __init__(self):
        self.master_ip = "127.0.0.1"
        self.master_port = 8888
        self.target_ip = "127.0.0.2"
        self.target_port = 8080
        with patch("qemii.detector.RdmaUDP.socket"):
            self.rdma = RdmaUDP(self.master_ip, self.master_port,
                                self.master_ip, self.master_port,
                                self.target_ip, self.target_port,
                                self.target_ip, self.target_port)


@pytest.fixture(scope="class")
def test_rdma():
    """Test Fixture for testing the RdmaUDP"""

    test_rdma = RdmaUDPTestFixture()
    yield test_rdma


class TestRdmaUDP():

    def test_init(self, test_rdma):
        test_rdma.rdma.rxsocket.bind.assert_called_with(
            (test_rdma.master_ip, test_rdma.master_port)
        )
        test_rdma.rdma.txsocket.bind.assert_called_with(
            (test_rdma.master_ip, test_rdma.master_port)
        )
