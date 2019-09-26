"""
Test Cases for the QEMII VectorFile in qemii.detector
Adam Neaves, STFC Detector Systems Software Group
"""

import sys
import os
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
        self.vector_data = [
            "000", "001", "010", "011", "100", "101", "110", "111",
            "000", "001", "010", "011", "100", "101", "110", "111",
            "000", "001", "010", "011", "100", "101", "110", "111", "000",
            "000", "001", "010", "011", "100", "101", "110", "111",
            "000", "001", "010", "011", "100", "101", "110", "111",
            "000", "001", "010", "011", "100", "101", "110", "111", "000"
        ]
        self.file ="{}\n{}".format('\n'.join((
            str(self.file_loop_pos), str(self.file_length), self.vector_names
        )), "\n".join(self.vector_data))
        self.file_name = "FakeName.test"
        self.file_dir = "/not/real/path"
        mocked_open = mock_open(read_data=self.file)
        with patch("qemii.detector.VectorFile.open", mocked_open, create=True):
            self.vector_file = VectorFile(self.file_name, self.file_dir)


@pytest.fixture
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

    def test_bias_to_raw(self, test_vector_file):
        test_vector_file.vector_file.bias["test_bias"] = 7
        test_vector_file.vector_file.bias["test_bias_2"] = 0
        test_vector_file.vector_file.convert_bias_to_raw()
        assert test_vector_file.vector_file.dac_data_vector == [
            "1", "1", "1", "0", "0", "0", "1", "1", "1", "0", "0", "0"]

    def test_get_set_bias(self, test_vector_file):
        test_vector_file.vector_file.set_bias_val("test_bias", 2)
        assert test_vector_file.vector_file.get_bias_val("test_bias") == 2
        assert test_vector_file.vector_file.dac_data_vector[0:3] == ["0", "1", "0"]
        assert test_vector_file.vector_file.dac_data_vector[6:9] == ["0", "1", "0"]

    def test_set_bias_same_val(self, test_vector_file):       
        with patch("qemii.detector.VectorFile.logging") as mocked_log:
            test_vector_file.vector_file.set_bias_val("test_bias", 5)
            mocked_log.debug.assert_called_once_with("Bias Already %d, ignoring", 5)

    def test_write_vector_file_current_file(self, test_vector_file):
        with patch('qemii.detector.VectorFile.open', mock_open()) as mocked_file:
            test_vector_file.vector_file.write_vector_file("")
            mocked_file.assert_called_once_with(
                os.path.join(test_vector_file.file_dir, test_vector_file.file_name),
                "w")
            handle = mocked_file()
            handle.write.assert_has_calls([
                call("{}\n".format(test_vector_file.file_loop_pos)),
                call("{}\n".format(test_vector_file.file_length)),
                call("\t".join(test_vector_file.vector_file.vector_names))
            ])
            for line in test_vector_file.vector_data:
                handle.write.assert_any_call("{}\n".format(line))

    def test_set_file_name(self, test_vector_file):
        fake_file = mock_open(read_data=test_vector_file.file)
        with patch('qemii.detector.VectorFile.open', fake_file) as mocked_file:
            new_file_name = "Differnt_fake_name"
            test_vector_file.vector_file.set_file_name(new_file_name)
            mocked_file.assert_called_once_with(os.path.join(
                test_vector_file.file_dir, new_file_name),
                "r"
            )

    def test_reset_vector_file(self, test_vector_file):
        fake_file = mock_open(read_data=test_vector_file.file)
        with patch('qemii.detector.VectorFile.open', fake_file) as mocked_file:
            os.path.isfile = Mock(return_value=True)
            test_vector_file.vector_file.set_bias_val("test_bias", 0)
            test_vector_file.vector_file.set_bias_val("test_bias_2", 7)
            test_vector_file.vector_file.reset_vector_file(None)

            mocked_file.assert_called_once_with(
                os.path.join(test_vector_file.file_dir, test_vector_file.file_name),
                "r")

            assert test_vector_file.vector_file.bias["test_bias"] == 5
            assert test_vector_file.vector_file.bias["test_bias_2"] == 2