import sys

import pytest


if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, MagicMock, patch
else:                         # pragma: no cover
    from mock import Mock, MagicMock, patch

sys.modules['odin_data.frame_processor_adapter'] = MagicMock()  # TODO: Hate this hacky way, find better
sys.modules['odin_data.frame_receiver_adapter'] = MagicMock()

from qemii.detector.adapter import QemDetectorAdapter


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
        with patch('qemii.detector.adapter.QemFem'), \
             patch('qemii.detector.adapter.QemDAQ'), \
             patch('qemii.detector.adapter.QemCalibrator'), \
             patch('qemii.detector.adapter.FrameProcessorAdapter'), \
             patch('qemii.detector.adapter.FrameReceiverAdapter'):

            self.adapter = QemDetectorAdapter(**self.options)
            self.path = "acquisition/num_frames"
            self.put_data = 1024
            self.request = Mock()
            self.request.configure_mock(
                headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                body=self.put_data
            )


@pytest.fixture
def test_detector_adapter():

    test_detector_adapter = DetectorAdapterTestFixture()
    yield test_detector_adapter


class TestDetectorAdapter():

    def test_adapter_get(self, test_detector_adapter):
        """Test that a call to the GET method of the detector adapter returns the correct response"""
        expected_response = {
            'num_frames': 4096
        }
        response = test_detector_adapter.adapter.get(
            test_detector_adapter.path,
            test_detector_adapter.request)
        assert response.data == expected_response
        assert response.status_code == 200

    def test_adapter_get_error(self, test_detector_adapter):
        false_path = "not/a/path"
        expected_response = {
            'error': "Invalid path: {}".format(false_path)
        }
        response = test_detector_adapter.adapter.get(
            false_path,
            test_detector_adapter.request)
        assert response.data == expected_response
        assert response.status_code == 400

    def test_adapter_put(self, test_detector_adapter):
        """Test that a normal call to the PUT method returns as expected"""
        expected_response = {
            'num_frames': test_detector_adapter.put_data
        }

        response = test_detector_adapter.adapter.put(
            test_detector_adapter.path,
            test_detector_adapter.request)
        assert response.data == expected_response
        assert response.status_code == 200
        assert test_detector_adapter.adapter.qem_detector.acq_num == test_detector_adapter.put_data

    def test_adapter_put_error(self, test_detector_adapter):
        false_path = "not/a/path"
        expected_response = {
            'error': "Failed to decode PUT request body: Invalid path: {}".format(false_path)
        }

        response = test_detector_adapter.adapter.put(
            false_path,
            test_detector_adapter.request)
        assert response.data == expected_response
        assert response.status_code == 400
        assert test_detector_adapter.adapter.qem_detector.acq_num == 4096
