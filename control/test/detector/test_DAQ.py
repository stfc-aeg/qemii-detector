"""
Test Cases for the QEMII DAQ in qemii.detector
Adam Neaves, STFC Detector Systems Software Group
"""

import sys
import pytest

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, MagicMock, call, patch
else:                         # pragma: no cover
    from mock import Mock, MagicMock, call, patch

from qemii.detector.QemDAQ import QemDAQ


class DAQTestFixture(object):

    def __init__(self):
        self.file_dir = "/fake/directory"
        self.file_name = "fake_file.txt"
        self.odin_data_dir = "/odin/data/dir"
        self.daq = QemDAQ(self.file_dir, self.file_name, self.odin_data_dir)


@pytest.fixture(scope="class")
def test_daq():
    """Test Fixture for testing the DAQ"""

    test_daq = DAQTestFixture()
    yield test_daq


class TestDAQ():

    def test_init(self, test_daq):
        assert test_daq.daq.file_dir == test_daq.file_dir
        assert test_daq.daq.file_name == test_daq.file_name
