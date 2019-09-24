"""
Test Cases for the QEMII VectorFile in qemii.detector
Adam Neaves, STFC Detector Systems Software Group
"""

import sys
import pytest

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, MagicMock, call, patch, mock_open
else:                         # pragma: no cover
    from mock import Mock, MagicMock, call, patch, mock_open

from qemii.detector.VectorFile import VectorFile


class VectorFileTestFixture(object):

    def __init__(self):
        VectorFile.BIAS_NAMES = ["test_bias", "test_bias_2"]
        VectorFile.BIAS_DEPTH = 3
        self.bias_vals = {"test_bias": 5, "test_bias_2": 2}
        self.file_length = 25
        self.file_loop_pos = 6
        self.vector_names = "dacDin dacCLKin unnamed"
        self.file = '\n'.join((
            str(self.file_loop_pos),
            str(self.file_length),
            self.vector_names,
            "000",
            "001",
            "010",
            "011",
            "100",
            "101",
            "110",
            "111",
            "000",
            "001",
            "010",
            "011",
            "100",
            "101",
            "110",
            "111",
            "000",
            "001",
            "010",
            "011",
            "100",
            "101",
            "110",
            "111",
            "000"
        ))
        self.file_name = "FakeName.test"
        self.file_dir = "/not/real/path"
        mocked_open = mock_open(read_data=self.file)
        with patch("qemii.detector.VectorFile.open", mocked_open, create=True):
            self.vector_file = VectorFile(self.file_name, self.file_dir)


@pytest.fixture(scope="class")
def test_vector_file():
    """Test Fixture for testing the VectorFile"""

    test_vector_file = VectorFileTestFixture()
    yield test_vector_file


class TestVectorFile():

    def test_init(self, test_vector_file):
        assert test_vector_file.vector_file.file_name == test_vector_file.file_name
        assert test_vector_file.vector_file.file_dir == test_vector_file.file_dir

    def test_bias_read(self, test_vector_file):
        for bias in test_vector_file.bias_vals:
            assert test_vector_file.bias_vals[bias] == test_vector_file.vector_file.bias[bias]
