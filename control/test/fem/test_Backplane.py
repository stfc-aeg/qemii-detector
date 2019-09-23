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

sys.modules['gpio'] = Mock()
sys.modules['smbus'] = MagicMock()

from qemii.fem.Backplane import Backplane


class BackplaneTestFixture(object):

    def __init__(self):

        self.backplane = Backplane()


@pytest.fixture(scope="class")
def test_backplane():
    """Basic text fixture for testing backplane adapter"""

    # mock/patch away the device drivers
    with patch("qemii.fem.Backplane.TCA9548") as mock_tca, \
         patch("qemii.fem.Backplane.MCP23008"), \
         patch("qemii.fem.Backplane.TPL0102"), \
         patch("qemii.fem.Backplane.SI570"), \
         patch("qemii.fem.Backplane.AD7998"), \
         patch("qemii.fem.Backplane.AD5694"):

        test_backplane = BackplaneTestFixture()
        yield test_backplane


class TestBackplane():

    def test_fake(self, test_backplane):

        assert True
