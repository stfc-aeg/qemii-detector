"""
Test cases for the Fem Adapter class in qemii_fem.
Adam Neaves, STFC Detector Systems Software Group
"""

import sys

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, call
else:                         # pragma: no cover
    from mock import Mock, call

import pytest

sys.modules['gpio'] = Mock()
from qemii_fem.adapters.FemAdapter import FemAdapter


class FemAdapterTestFixture(object):

    def __init__(self):
        self.adapter = FemAdapter()
        self.request = Mock()
        self.path = "control/"
        self.request.headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}


@pytest.fixture(scope="class")
def test_fem_adapter():
    """Basic text fixture for testing fem adapter"""
    test_fem_adapter = FemAdapterTestFixture()
    yield test_fem_adapter


class TestFemAdapter():

    def test_adapter_get(self, test_fem_adapter):
        response = test_fem_adapter.adapter.get(test_fem_adapter.path,
                                                test_fem_adapter.request)
        assert response.status_code == 200