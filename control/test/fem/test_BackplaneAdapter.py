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

from qemii.fem.BackplaneAdapter import BackplaneAdapter


class BackplaneAdapterTestFixture(object):

    def __init__(self):
        with patch("qemii.fem.BackplaneAdapter.Backplane"):
            self.adapter = BackplaneAdapter()
            self.request = Mock()
            self.path = "control/"
            self.request.headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}


@pytest.fixture(scope="class")
def test_backplane_adapter():
    """Basic text fixture for testing backplane adapter"""
    test_backplane_adapter = BackplaneAdapterTestFixture()
    yield test_backplane_adapter


class TestBackplaneAdapter():

    def test_adapter_get(self, test_backplane_adapter):
        print("Backplane Module: " + test_backplane_adapter.adapter.backplane.__module__)
        response = test_backplane_adapter.adapter.get(test_backplane_adapter.path,
                                                      test_backplane_adapter.request)
        assert response.status_code == 200