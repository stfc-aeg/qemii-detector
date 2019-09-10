import sys

import pytest

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, MagicMock
else:                         # pragma: no cover
    from mock import Mock, MagicMock

# mocking some modules to avoid issues from them trying to access
# files or IP addresses while testing
sys.modules['socket'] = MagicMock()
sys.modules['qemii_detector.QemFem'] = Mock() 

from qemii_detector.QemDetectorAdapter import QemDetectorAdapter


class DetectorAdapterTestFixture(object):

    def __init__(self):
        self.options = {
            "fem_0":
                """
                ip_addr = 192.168.0.122,
                port = 8070,
                id = 0,
                server_ctrl_ip = 127.0.0.1,
                camera_ctrl_ip = 127.0.0.1,
                server_data_ip = 127.0.0.1,
                camera_data_ip = 127.0.0.1
                """
        }
        self.adapter = QemDetectorAdapter(**self.options)
        self.path = "acquisition/num_frames"
        self.request = Mock()
        self.request.headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}


@pytest.fixture(scope="class")
def test_detector_adapter():
    test_detector_adapter = DetectorAdapterTestFixture()
    yield test_detector_adapter


class TestDetectorAdapter():

    def test_adapter_get(self, test_detector_adapter):
        """Test that a call to the GET method of the detector adapter returns the correct response"""
        expected_response = {
            'num_frames': 4096
        }
        response = test_detector_adapter.adapter.get(test_detector_adapter.path, test_detector_adapter.request)
        assert response.data == expected_response
        assert response.status_code == 200
