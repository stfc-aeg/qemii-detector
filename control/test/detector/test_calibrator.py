"""
Test Cases for the QEMII Calibrator class in qemii.detector
Adam Neaves, STFC Detector Systems Software Group
"""

import sys
import pytest
import logging
from qemii.detector.QemCalibrator import QemCalibrator
from qemii.detector.QemCalibrator import VOLT_OFFSET_BASE, VOLT_MULTIPLY_COARSE, VOLT_MULTIPLY_FINE
from qemii.detector.QemCalibrator import COARSE_BIT_MASK, FINE_BIT_MASK

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, MagicMock, call, patch, ANY
else:                         # pragma: no cover
    from mock import Mock, MagicMock, call, patch, ANY


def log_message_seen(caplog, level, message):  # TODO: put this in a test util thing
    """Test if a certain message of a certain level exists in the captured log"""
    for record in caplog.records:
        if record.levelno == level and message in record.getMessage():
            return True

    return False


def fake_proxy_return(adapter, request):
    request_data = request.body
    return_mock = Mock()

    register_names = ["AUXSAMPLE_COARSE", "AUXSAMPLE_FINE"]
    if any(x in request_data for x in register_names):
        return_mock.configure_mock(status_code=200)
    else:
        return_mock.configure_mock(status_code=404, data="KEY NOT FOUND")
    return return_mock


class CalibratorTestFixture(object):

    def __init__(self):
        self.coarse_calibration_val = 2000
        self.fems = [Mock()]
        self.fems[0].get_idelay_lock_status = Mock(return_value=False)
        self.daq = Mock(file_dir="fake/file/dir", file_name="fake_file", in_progress=False)
        self.fake_proxy = Mock()
        self.fake_proxy.put = Mock(side_effect=fake_proxy_return)
        self.adapters = {"proxy": self.fake_proxy}
        with patch("qemii.detector.QemCalibrator.ParameterTree"):
            self.calibrator = QemCalibrator(self.coarse_calibration_val, self.fems, self.daq)

        self.calibrator.initialize(self.adapters)

        self.fake_image_data = [
            [((31 - ((8 * row) + column)) << 6) | ((8 * row) + column)
             for column in range(8)] for row in range(4)]

        printable = ""
        for row in self.fake_image_data:
            printable += "\n["
            for column in row:
                printable += "{:012b},".format(column)
        logging.debug("Fake Data:\n%s", printable)


@pytest.fixture
def test_calibrator():
    """Test Fixture for testing the Calibrator"""

    test_calibrator = CalibratorTestFixture()
    yield test_calibrator


class TestCalibrator():

    def test_init(self, test_calibrator):
        """Test values are correctly setup when initing the class."""
        with patch("qemii.detector.QemCalibrator.ParameterTree"):
            calibrator = QemCalibrator(test_calibrator.coarse_calibration_val, test_calibrator.fems, test_calibrator.daq)

        assert calibrator.coarse_calibration_value == test_calibrator.coarse_calibration_val
        assert calibrator.fems == test_calibrator.fems
        assert calibrator.daq == test_calibrator.daq

    def test_initialize(self, test_calibrator, caplog):
        """Test the initialize method correctly handles the dict of loaded adapters,
        both when the proxy adapter does and does not exist."""
        with patch("qemii.detector.QemCalibrator.ParameterTree"):
            calibrator = QemCalibrator(test_calibrator.coarse_calibration_val, test_calibrator.fems, test_calibrator.daq)

        test_adapters = {
            "Not_proxy": Mock(),
            "adapter": Mock()
        }
        calibrator.initialize(test_adapters)

        assert calibrator.proxy_adapter == None
        assert log_message_seen(caplog, logging.ERROR, "Cannot Initialize Calibrator:")
        caplog.clear()

        calibrator.initialize(test_calibrator.adapters)

        assert calibrator.proxy_adapter == test_calibrator.adapters["proxy"]
        assert not log_message_seen(caplog, logging.ERROR, "Cannot Initialize Calibrator:")

    def test_generate_coarse_voltages(self, test_calibrator):
        """Ensure the method returns a list of voltages as expected"""
        volt_range = 10
        expected_voltages = [float(VOLT_OFFSET_BASE + (i * VOLT_MULTIPLY_COARSE)) for i in range(volt_range)]
        voltages = test_calibrator.calibrator.generate_coarse_voltages(volt_range)

        assert voltages == expected_voltages

    def test_generate_fine_voltages(self, test_calibrator):
        """Ensure the method returns a list of voltages as expected"""
        volt_range = 10
        offset = VOLT_OFFSET_BASE + (VOLT_MULTIPLY_COARSE * test_calibrator.coarse_calibration_val)

        expected_voltages = [float(offset + (i * VOLT_MULTIPLY_FINE)) for i in range(volt_range)]

        voltages = test_calibrator.calibrator.generate_fine_voltages(volt_range)

        assert voltages == expected_voltages

    def test_set_max_calib(self, test_calibrator):
        """Test the set method, making sure it cannot go over the maximum"""
        test_calibrator.calibrator.set_max_calib(1024)
        assert test_calibrator.calibrator.max_calibration == 1024
        test_calibrator.calibrator.set_max_calib(10000)
        assert test_calibrator.calibrator.max_calibration == 4096

    def test_set_min_calib(self, test_calibrator):
        """Test the set method, making sure it cannot go under the minimum"""
        test_calibrator.calibrator.set_min_calib(100)
        assert test_calibrator.calibrator.min_calibration == 100
        test_calibrator.calibrator.set_min_calib(-1000)
        assert test_calibrator.calibrator.min_calibration == 0

    def test_set_calib_step(self, test_calibrator):
        """Test the set method, making sure it cannot go under the minimum"""
        test_calibrator.calibrator.set_calib_step(10)
        assert test_calibrator.calibrator.calibration_step == 10
        test_calibrator.calibrator.set_calib_step(0)
        assert test_calibrator.calibrator.calibration_step == 1

    def test_set_backplane_register(self, test_calibrator, caplog):
        """Test that the method calls the put method of the proxy adapter correctly"""
        test_calibrator.calibrator.set_backplane_register("AUXSAMPLE_COARSE", 345)

        test_calibrator.fake_proxy.put.assert_called_with("backplane", ANY)
        assert not log_message_seen(caplog, logging.ERROR, "BACKPLANE REGISTER SET FAILED:")

        test_calibrator.calibrator.set_backplane_register("NOT_REGISTER", 12345)

        test_calibrator.fake_proxy.put.assert_called_with("backplane", ANY)
        assert log_message_seen(caplog, logging.ERROR, "BACKPLANE REGISTER SET FAILED")

    def test_get_fine_bits_column(self, test_calibrator):
        """Test that the fine bits are extracted properly from the data"""
        expected_data = [0, 8, 16, 24]
        data = test_calibrator.calibrator.get_fine_bits_column(test_calibrator.fake_image_data, 0)
        assert expected_data == data

        expected_data = [2, 10, 18, 26]
        data = test_calibrator.calibrator.get_fine_bits_column(test_calibrator.fake_image_data, 2)
        assert expected_data == data

    def test_get_coarse_bits_column(self, test_calibrator):
        """Test that the coarse bits are extracted properly from the data"""
        expected_data = [31, 23, 15, 7]
        data = test_calibrator.calibrator.get_coarse_bits_column(test_calibrator.fake_image_data, 0)
        assert expected_data == data

        expected_data = [29, 21, 13, 5]
        data = test_calibrator.calibrator.get_coarse_bits_column(test_calibrator.fake_image_data, 2)
        assert expected_data == data

    def test_get_h5_file(self, test_calibrator):
        """Test that the method returns the h5 file name properly"""
        with patch("qemii.detector.QemCalibrator.glob") as mock_glob:
            mock_glob.glob = Mock(return_value=["not_looking_for.h5", "fake_file_0001.h5"])

            h5_file = test_calibrator.calibrator.get_h5_file()
            assert "fake_file_0001.h5" == h5_file

            mock_glob.glob = Mock(return_value=["not_looking_for.h5", "not_file_either.h5"])
            h5_file = test_calibrator.calibrator.get_h5_file()
            assert "not_found" == h5_file

    def test_calibration_loop(self, test_calibrator):
        """Test that the loop correctly calls itself"""
        calibrator = test_calibrator.calibrator  # shorten some of the following lines

        calibrator.max_calibration = 10
        calibrator.calibration_step = 2
        calibrator.calibration_value = 0
        with patch("qemii.detector.QemCalibrator.IOLoop") as mock_loop:
            calibrator.calibration_loop("AUXSAMPLE_COARSE")

            test_calibrator.fems[0].frame_gate_settings.assert_called_with(0, 0)
            assert test_calibrator.fems[0].frame_gate_trigger.called
            assert calibrator.calibration_value == 2
            mock_loop.instance().call_later.assert_called_with(0, calibrator.calibration_loop, "AUXSAMPLE_COARSE")

            calibrator.calibration_value = 8
            calibrator.calibration_loop("AUXSAMPLE_COARSE")

            assert calibrator.calibration_value == 10
            mock_loop.instance.call_later.assert_not_called()

    def test_coarse_calibrate(self, test_calibrator):
        """Test that the method starts the calibration correctly"""
        with patch("qemii.detector.QemCalibrator.IOLoop") as mock_loop:
            calibrator = test_calibrator.calibrator
            calibrator.set_backplane_register = Mock()
            calibrator.adc_calibrate("coarse")

            mock_loop.instance().add_callback.assert_called_with(calibrator.calibration_loop, register="AUXSAMPLE_COARSE")
            assert test_calibrator.fems[0].setup_camera.called
            assert test_calibrator.fems[0].load_vectors_from_file.called
            calibrator.set_backplane_register.assert_called_with("AUXSAMPLE_FINE", calibrator.max_calibration - 1)

    def test_fine_calibrate(self, test_calibrator):
        """Test that the method starts the calibration correctly"""
        with patch("qemii.detector.QemCalibrator.IOLoop") as mock_loop:
            calibrator = test_calibrator.calibrator
            calibrator.set_backplane_register = Mock()
            calibrator.adc_calibrate("fine")

            mock_loop.instance().add_callback.assert_called_with(calibrator.calibration_loop, register="AUXSAMPLE_FINE")
            assert test_calibrator.fems[0].setup_camera.called
            assert test_calibrator.fems[0].load_vectors_from_file.called
            calibrator.set_backplane_register.assert_called_with("AUXSAMPLE_COARSE", calibrator.coarse_calibration_value)

    def test_adc_calibrate_in_progress(self, test_calibrator):
        """Test that the method correctly exits if an aquisition is already in progress"""

        test_calibrator.daq.in_progress = True
        with patch("qemii.detector.QemCalibrator.IOLoop") as mock_loop:
            calibrator = test_calibrator.calibrator
            calibrator.adc_calibrate("fine")

            mock_loop.instance().add_callback.assert_not_called()
            test_calibrator.fems[0].setup_camera.assert_not_called()
            test_calibrator.fems[0].load_vectors_from_file.assert_not_called()

    def test_adc_calibrate_bad_type(self, test_calibrator):
        """Test that the method correctly exits if the type of calibration is not specified correctly"""
        with patch("qemii.detector.QemCalibrator.IOLoop") as mock_loop:
            calibrator = test_calibrator.calibrator
            calibrator.set_backplane_register = Mock()
            calibrator.adc_calibrate("incorrect_type")

            mock_loop.instance().add_callback.assert_not_called()
            test_calibrator.fems[0].setup_camera.assert_not_called()
            test_calibrator.fems[0].load_vectors_from_file.assert_not_called()

    def test_adc_plot_coarse(self, test_calibrator):
        """Test that the plot method runs properly"""
        with patch("qemii.detector.QemCalibrator.plt") as mock_plt, \
             patch("qemii.detector.QemCalibrator.h5py") as mock_h5:

            mock_file = MagicMock()
            mock_file.__getitem__.return_value = [test_calibrator.fake_image_data]
            mock_h5.File.return_value = mock_file

            calibrator = test_calibrator.calibrator
            calibrator.max_calibration = 1
            calibrator.min_calibration = 0
            calibrator.calibration_column = 3
            calibrator.generate_coarse_voltages = Mock()

            calibrator.adc_plot("coarse")

            assert calibrator.generate_coarse_voltages.called
            assert mock_plt.figure.called
            mock_plt.figure().savefig.assert_called_with("static/img/coarse_graph.png", dpi=100)

    def test_adc_plot_fine(self, test_calibrator):
        """Test that the plot method runs properly"""
        with patch("qemii.detector.QemCalibrator.plt") as mock_plt, \
             patch("qemii.detector.QemCalibrator.h5py") as mock_h5:

            mock_file = MagicMock()
            mock_file.__getitem__.return_value = [test_calibrator.fake_image_data]
            mock_h5.File.return_value = mock_file

            calibrator = test_calibrator.calibrator
            calibrator.max_calibration = 1
            calibrator.min_calibration = 0
            calibrator.calibration_column = 3
            calibrator.generate_fine_voltages = Mock()

            calibrator.adc_plot("fine")

            assert calibrator.generate_fine_voltages.called
            assert mock_plt.figure.called
            mock_plt.figure().savefig.assert_called_with("static/img/fine_graph.png", dpi=100)

    def test_adc_plot_busy(self, test_calibrator):
        """Test that the plot method correctly exits if the daq is busy"""
        calibrator = test_calibrator.calibrator
        test_calibrator.daq.in_progress = True
        calibrator.generate_fine_voltages = Mock()
        calibrator.generate_coarse_voltages = Mock()
        with patch("qemii.detector.QemCalibrator.plt") as mock_plt, \
             patch("qemii.detector.QemCalibrator.h5py") as mock_h5:

            calibrator = test_calibrator.calibrator
            calibrator.adc_plot("coarse")

            calibrator.generate_coarse_voltages.assert_not_called()
            calibrator.generate_fine_voltages.assert_not_called()
            mock_plt.figure.assert_not_called()

    def test_adc_plot_bad_type(self, test_calibrator):
        """Test that the plot method correctly exits if the plot type is invalid"""
        calibrator = test_calibrator.calibrator
        calibrator.generate_fine_voltages = Mock()
        calibrator.generate_coarse_voltages = Mock()
        with patch("qemii.detector.QemCalibrator.plt") as mock_plt, \
             patch("qemii.detector.QemCalibrator.h5py") as mock_h5:

            calibrator = test_calibrator.calibrator
            calibrator.adc_plot("invalid_type")

            calibrator.generate_coarse_voltages.assert_not_called()
            calibrator.generate_fine_voltages.assert_not_called()
            mock_plt.figure.assert_not_called()



