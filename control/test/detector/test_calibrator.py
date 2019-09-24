"""
Test Cases for the QEMII Calibrator class in qemii.detector
Adam Neaves, STFC Detector Systems Software Group
"""

import sys
import pytest

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, MagicMock, call, patch
else:                         # pragma: no cover
    from mock import Mock, MagicMock, call, patch


from qemii.detector.QemCalibrator import QemCalibrator


class CalibratorTestFixture(object):

    def __init__(self):
        self.coarse_calibration_val = 2000
        self.fems = [Mock()]
        self.daq = Mock()
        self.calibrator = QemCalibrator(self.coarse_calibration_val, self.fems, self.daq)


@pytest.fixture(scope="class")
def test_calibrator():
    """Test Fixture for testing the Calibrator"""

    test_calibrator = CalibratorTestFixture()
    yield test_calibrator


class TestCalibrator():

    def test_init(self, test_calibrator):
        assert isinstance(test_calibrator.calibrator, QemCalibrator)
        assert test_calibrator.calibrator.coarse_calibration_value == test_calibrator.coarse_calibration_val