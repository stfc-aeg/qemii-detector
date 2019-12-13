"""
Test cases for the Backplane Adapter class in qemii.fem.
Adam Neaves, STFC Detector Systems Software Group
"""

import sys
import pytest

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, MagicMock, call, patch
else:                         # pragma: no cover
    from mock import Mock, MagicMock, call, patch

# TODO: still hacky, still hate it
sys.modules['gpio'] = Mock()
sys.modules['smbus'] = MagicMock()

from qemii.fem.Backplane import Backplane


class BackplaneTestFixture(object):

    def __init__(self):
        with patch("qemii.fem.Backplane.TCA9548") as mock_tca, \
             patch("qemii.fem.Backplane.MCP23008") as mock_mcp, \
             patch("qemii.fem.Backplane.TPL0102") as mock_tpl, \
             patch("qemii.fem.Backplane.SI570") as mock_si, \
             patch("qemii.fem.Backplane.AD7998") as mock_ad7, \
             patch("qemii.fem.Backplane.AD5694") as mock_ad5, \
             patch("qemii.fem.Backplane.ParameterTree"):

            self.backplane = Backplane()
            self.tca = mock_tca
            self.mcp = mock_mcp
            self.tpl = mock_tpl
            self.si = mock_si
            self.ad5 = mock_ad5
            self.ad7 = mock_ad7


@pytest.fixture(scope="class")
def test_backplane():
    """Basic text fixture for testing backplane adapter"""

    # mock/patch away the device drivers

    test_backplane = BackplaneTestFixture()
    yield test_backplane


class TestBackplane():


    def test_init(self, test_backplane):
        """Test that the backplane class gets initialised properly"""
        # backplane is initialized in the fixture, just assert
        assert test_backplane.backplane.backplane_power
        assert test_backplane.backplane.clock_frequency == 17.5
        assert test_backplane.backplane.tca.attach_device.called
        assert len(test_backplane.backplane.voltages) == 16

    def test_set_backplane_power(self, test_backplane):

        test_backplane.backplane.set_backplane_power(False)
        assert test_backplane.backplane.backplane_power is False

        test_backplane.backplane.set_backplane_power(True)
        assert test_backplane.backplane.backplane_power is True

    def test_i2c_init(self, test_backplane):
        """Test that the i2c init method instantiates objects correctly"""
        # method called during init from fiture, just assert
        assert len(test_backplane.backplane.tpl0102) == 4
        assert len(test_backplane.backplane.ad7998) == 4
        test_backplane.backplane.tca.attach_device.asssert_has_calls([
            call(0, test_backplane.tpl, 0x50, busnum=1),
            call(2, test_backplane.ad7, 0x21, busnum=1),
            call(0, test_backplane.tpl, 0x51, busnum=1),
            call(2, test_backplane.ad7, 0x22, busnum=1),
            call(0, test_backplane.tpl, 0x52, busnum=1),
            call(2, test_backplane.ad7, 0x23, busnum=1),
            call(0, test_backplane.tpl, 0x53, busnum=1),
            call(2, test_backplane.ad7, 0x24, busnum=1),
        ])
        assert len(test_backplane.backplane.adjust_resistor_raw) == 8
        test_backplane.backplane.ad5694.read_dac_value.assert_has_calls([
            call(1),
            call(4)
        ])

    def test_set_vdd_register(self, test_backplane):

        test_backplane.backplane.set_vdd_rst_register_value(100)
        test_backplane.backplane.tpl0102[2].set_wiper.assert_called_with(0, 100)

    def test_set_vdd_voltage(self, test_backplane):
        """Test if setting the voltage of the VDD produces the correct output"""

        test_backplane.backplane.set_vdd_rst_voltage(1.8)
        test_backplane.backplane.tpl0102[2].set_wiper.assert_called_with(0, 1)

        test_backplane.backplane.set_vdd_rst_voltage(3.3)
        test_backplane.backplane.tpl0102[2].set_wiper.assert_called_with(0, 237)

    def test_set_vreset_register(self, test_backplane):

        test_backplane.backplane.set_vreset_register_value(100)
        test_backplane.backplane.tpl0102[2].set_wiper.assert_called_with(1, 100)

    def test_set_vreset_voltage(self, test_backplane):

        test_backplane.backplane.set_vreset_voltage(0)
        test_backplane.backplane.tpl0102[2].set_wiper.assert_called_with(1, 1)

        test_backplane.backplane.set_vreset_voltage(3.3)
        test_backplane.backplane.tpl0102[2].set_wiper.assert_called_with(1, 250)

    def test_set_vctrl_register(self, test_backplane):

        test_backplane.backplane.set_vctrl_register_value(100)
        test_backplane.backplane.tpl0102[3].set_wiper.assert_called_with(0, 100)

    def test_set_vctrl_voltage(self, test_backplane):

        test_backplane.backplane.set_vctrl_voltage(-2)
        test_backplane.backplane.tpl0102[3].set_wiper.assert_called_with(0, 1)

        test_backplane.backplane.set_vctrl_voltage(3.3)
        test_backplane.backplane.tpl0102[3].set_wiper.assert_called_with(0, 250)

    def test_set_aux_vcm_register(self, test_backplane):

        test_backplane.backplane.set_aux_vcm_register_value(0, 0, 100)
        test_backplane.backplane.tpl0102[0].set_wiper.assert_called_with(0, 100)

    def test_set_aux_vcm_voltage(self, test_backplane):

        test_backplane.backplane.set_aux_vcm_voltage(0, 0, 0)
        test_backplane.backplane.tpl0102[0].set_wiper.assert_called_with(0, 0)

        test_backplane.backplane.set_aux_vcm_voltage(0, 0, 2.5)
        test_backplane.backplane.tpl0102[0].set_wiper.assert_called_with(0, 256)

    def test_set_auxreset_register(self, test_backplane):

        test_backplane.backplane.set_auxreset_register_value(100)
        test_backplane.backplane.tpl0102[0].set_wiper.assert_called_with(0, 100)

    def test_set_auxreset_voltage(self, test_backplane):
        
        test_backplane.backplane.set_auxreset_voltage(0)
        test_backplane.backplane.tpl0102[0].set_wiper.assert_called_with(0, 0)

        test_backplane.backplane.set_auxreset_voltage(2.5)
        test_backplane.backplane.tpl0102[0].set_wiper.assert_called_with(0, 256)

    def test_set_vcm_register(self, test_backplane):

        test_backplane.backplane.set_vcm_register_value(100)
        test_backplane.backplane.tpl0102[0].set_wiper.assert_called_with(1, 100)

    def test_set_vcm_voltage(self, test_backplane):
        
        test_backplane.backplane.set_vcm_voltage(0)
        test_backplane.backplane.tpl0102[0].set_wiper.assert_called_with(1, 0)

        test_backplane.backplane.set_vcm_voltage(2.5)
        test_backplane.backplane.tpl0102[0].set_wiper.assert_called_with(1, 256)