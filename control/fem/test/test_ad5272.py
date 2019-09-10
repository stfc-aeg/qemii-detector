"""Test Cases for the AD5272 class from odin_devices
Adam Neaves, STFC Detector Systems Software Group
"""

import sys

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, call
else:                         # pragma: no cover
    from mock import Mock, call

import pytest

sys.modules['smbus'] = Mock()
from qemii_fem.devices.ad5272 import AD5272
from qemii_fem.devices.i2c_device import I2CDevice, I2CException

class TestAD5272():

    def test_fake(self):
        # dummy test case as placeholder
        assert True == True
