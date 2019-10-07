"""
Test Cases for the QEMII Fem in qemii.detector
Adam Neaves, STFC Detector Systems Software Group
"""

import sys
import pytest

from qemii.detector.QemFem import QemFem

if sys.version_info[0] == 3:  # pragma: no cover
    from unittest.mock import Mock, MagicMock, call, patch, ANY
else:                         # pragma: no cover
    from mock import Mock, MagicMock, call, patch, ANY


class FemTestFixture(object):

    def __init__(self):

        self.ip = "127.0.0.1"
        self.port = 8888
        self.id = 0
        self.frame_size = 7344

        self.rdma_addr = {
            "udp_10G_data":    0x00000000,
            "udp_10G_control": 0x10000000,
            "sequencer":       0xB0000000,
            "receiver":        0xC0000000,
            "frm_gate":        0xD0000000
        }

        self.vector_file_dir = "fake/vector/file/dir"
        self.vector_file = "FakeVectorFile.txt"
        self.vector_length = 3
        self.vector_loop = 1
        self.vector_data = [
            [1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1],
            [0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0],
            [1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1],
        ]

        with patch("qemii.detector.QemFem.VectorFile"):
            with patch("qemii.detector.QemFem.RdmaUDP"):
                self.fem = QemFem(self.ip, self.port, self.id,
                                  self.ip, self.ip, self.ip, self.ip,
                                  self.vector_file_dir,
                                  self.vector_file)
                self.fem.connect()

                self.fem.vector_file.configure_mock(
                    file_dir=self.vector_file_dir,
                    file_name=self.vector_file,
                    vector_loop_position=self.vector_loop,
                    vector_length=self.vector_length,
                    vector_data=self.vector_data)

        self.ifg_call_list = [
            call(self.rdma_addr["udp_10G_data"] + 0xF, 0, ANY),
            call(self.rdma_addr['udp_10G_data'] + 0xD, 3, ANY),
            call(self.rdma_addr['udp_10G_control'] + 0xF, 0, ANY),
            call(self.rdma_addr['udp_10G_control'] + 0xD, 3, ANY)
        ]

        self.start_stop_sequencer_call_list = [
            call(self.rdma_addr["sequencer"], 0, ANY),
            call(self.rdma_addr["sequencer"], 2, ANY),
            call(self.rdma_addr["sequencer"], 0, ANY),
            call(self.rdma_addr["sequencer"], 1, ANY)

        ]

        self.set_idelay_call_list = [
            call(self.rdma_addr["receiver"] | 0x02, 0, ANY),
            call(self.rdma_addr["receiver"], 0, ANY),
            call(self.rdma_addr["receiver"], 16, ANY),
            call(self.rdma_addr["receiver"], 0, ANY)
        ]

        self.image_size_call_list = [
            call(self.rdma_addr["receiver"] | 0x01, 143, ANY),
            call(self.rdma_addr["receiver"] + 4, 1, ANY)
        ]

        self.load_vectors_call_list = [
            # stop sequencer
            call(self.rdma_addr["sequencer"], 0, ANY),
            call(self.rdma_addr["sequencer"], 2, ANY),
            # upload vector data
            call(self.rdma_addr["sequencer"] + 0x01000000 + 0, 0xa5a5a5a5, ANY),
            call(self.rdma_addr['sequencer'] + 0x01000000 + 1, 0xa5a5a5a5, ANY),
            call(self.rdma_addr['sequencer'] + 0x01000000 + 2, 0x5a5a5a5a, ANY),
            call(self.rdma_addr['sequencer'] + 0x01000000 + 3, 0x5a5a5a5a, ANY),
            call(self.rdma_addr['sequencer'] + 0x01000000 + 4, 0xa5a5a5a5, ANY),
            call(self.rdma_addr['sequencer'] + 0x01000000 + 5, 0xa5a5a5a5, ANY),
            # loop limit
            call(self.rdma_addr['sequencer'] + 1, self.vector_loop - 1, ANY),
            call(self.rdma_addr['sequencer'] + 2, self.vector_length - 1, ANY),
            # start sequencer
            call(self.rdma_addr["sequencer"], 0, ANY),
            call(self.rdma_addr["sequencer"], 1, ANY)
        ]


@pytest.fixture()
def test_fem():
    """Test Fixture for testing the Fem"""

    test_fem = FemTestFixture()
    yield test_fem


class TestFem():

    def test_init(self, test_fem):
        """Assert the initilisation of the Fem class works"""
        assert test_fem.fem.ip_address == test_fem.ip
        assert test_fem.fem.vector_file_dir == test_fem.vector_file_dir
        assert test_fem.fem.id == test_fem.id

    def test_nonzero_id(self, test_fem):
        """Assert the vector file is ignored if ID is not 0"""
        fem = QemFem(test_fem.ip, test_fem.port, 1,
                     test_fem.ip, test_fem.ip, test_fem.ip, test_fem.ip,
                     test_fem.vector_file_dir,
                     test_fem.vector_file)
        assert fem.id == 1
        assert fem.vector_file is None
        assert fem.vector_file_dir is None

    def test_connect(self, test_fem):
        """Assert the connect method creates the rdma as expected"""
        with patch("qemii.detector.QemFem.RdmaUDP") as mock_rdma:
            test_fem.fem.connect()

            mock_rdma.assert_called_with(test_fem.ip, 61650,
                                         test_fem.ip, 61651,
                                         test_fem.ip, 61650,
                                         test_fem.ip, 61651,
                                         2000000, 9000, 20)
            assert test_fem.fem.x10g_rdma.ack is True

    def test_set_ifg(self, test_fem):
        """Assert that set_ifg calls the write method of the rdma correctly"""
        test_fem.fem.set_ifg()

        test_fem.fem.x10g_rdma.write.assert_has_calls(test_fem.ifg_call_list)

        assert len(test_fem.ifg_call_list) == test_fem.fem.x10g_rdma.write.call_count

    def test_setup_camera(self, test_fem):

        test_fem.fem.setup_camera()

        call_list = []
        call_list.extend(test_fem.ifg_call_list)  # calls set_ifg
        # calls set_10g_mtu
        call_list.append(call(test_fem.rdma_addr['udp_10G_data'] + 0xC,
                              test_fem.frame_size / 8 - 2, ANY))
        # calls set_image_size
        call_list.extend(test_fem.image_size_call_list)
        # calls set idelay
        call_list.extend(test_fem.set_idelay_call_list)
        # calls set_scsr
        call_list.append(call(test_fem.rdma_addr['receiver'] | 0x05, 0x07070707, ANY))
        # calls set_ivsr
        call_list.append(call(test_fem.rdma_addr['receiver'] | 0x03, 0x1B1B, ANY))

        test_fem.fem.x10g_rdma.write.assert_has_calls(call_list)

    def test_restart_sequencer(self, test_fem):

        test_fem.fem.restart_sequencer()

        test_fem.fem.x10g_rdma.write.assert_has_calls(test_fem.start_stop_sequencer_call_list)

    def test_get_aligner_status(self, test_fem):

        test_fem.fem.x10g_rdma.read = Mock(return_value=0xDEADBEEF)
        address = test_fem.rdma_addr["receiver"] | 0x14
        status = test_fem.fem.get_aligner_status()

        test_fem.fem.x10g_rdma.read.assert_called_with(address, ANY)
        assert status == [0xDEAD, 0xBEEF]

    def test_set_idelay(self, test_fem):
        test_fem.fem.set_idelay()

        test_fem.fem.x10g_rdma.write.assert_has_calls(test_fem.set_idelay_call_list)

        test_fem.fem.set_idelay()

    def test_idelay_lock_status(self, test_fem):
        test_fem.fem.x10g_rdma = None
        status = test_fem.fem.get_idelay_lock_status()
        assert status == 0

        with patch("qemii.detector.QemFem.RdmaUDP"):
            test_fem.fem.connect()

            read_mock = Mock(return_value=0x000000F1)
            test_fem.fem.x10g_rdma.read = read_mock

            status = test_fem.fem.get_idelay_lock_status()
            assert status == 1

    def test_set_10g_mtu(self, test_fem):
        test_fem.fem.set_10g_mtu('control', 256)
        assert test_fem.fem.rdma_mtu == 256
        test_fem.fem.x10g_rdma.write.assert_called_with(
            test_fem.rdma_addr['udp_10G_control'] + 0xC,
            256 // 8 - 2,
            ANY
        )

        test_fem.fem.set_10g_mtu('data', 1024)
        assert test_fem.fem.strm_mtu == 1024
        test_fem.fem.x10g_rdma.write.assert_called_with(
            test_fem.rdma_addr['udp_10G_data'] + 0xC,
            1024 // 8 - 2,
            ANY
        )

    def test_set_ivsr(self, test_fem):

        address = test_fem.rdma_addr["receiver"] | 0x03

        test_fem.fem.set_ivsr(0, 0, 0, 0)
        test_fem.fem.x10g_rdma.write.assert_called_with(
            address, 0, ANY
        )

        test_fem.fem.set_ivsr(16, 16, 16, 16)
        test_fem.fem.x10g_rdma.write.assert_called_with(
            address, 0x10101010, ANY
        )

        test_fem.fem.set_ivsr(0x5a, 0x5b, 0x5c, 0x5d)
        test_fem.fem.x10g_rdma.write.assert_called_with(
            address, 0x5a5b5c5d, ANY
        )

        with pytest.raises(TypeError) as exc_info:
            test_fem.fem.set_ivsr(0.1, 0.2, 0.3, 0.4)
        assert exc_info.type is TypeError
        assert exc_info.value.args[0] == "unsupported operand type(s) for <<: 'float' and 'int'"

    def test_set_scsr(self, test_fem):

        address = test_fem.rdma_addr["receiver"] | 0x05

        test_fem.fem.set_scsr(0, 0, 0, 0)
        test_fem.fem.x10g_rdma.write.assert_called_with(
            address, 0, ANY
        )

        test_fem.fem.set_scsr(16, 16, 16, 16)
        test_fem.fem.x10g_rdma.write.assert_called_with(
            address, 0x10101010, ANY
        )

        test_fem.fem.set_scsr(0x5a, 0x5b, 0x5c, 0x5d)
        test_fem.fem.x10g_rdma.write.assert_called_with(
            address, 0x5a5b5c5d, ANY
        )

        with pytest.raises(TypeError) as exc_info:
            test_fem.fem.set_scsr(0.1, 0.2, 0.3, 0.4)
        assert exc_info.type is TypeError
        assert exc_info.value.args[0] == "unsupported operand type(s) for <<: 'float' and 'int'"

    def test_set_image_size(self, test_fem):

        address_pixel_count = test_fem.rdma_addr['receiver'] | 1
        address_pixel_size = test_fem.rdma_addr['receiver'] + 4

        test_fem.fem.set_image_size(102, 288, 11, 16)

        assert test_fem.fem.image_size_x == 102
        assert test_fem.fem.image_size_y == 288
        assert test_fem.fem.image_size_p == 11
        assert test_fem.fem.image_size_f == 16

        data = (0x1FFFF & (288 // 2)) - 1
        test_fem.fem.x10g_rdma.write.assert_has_calls(
            [call(address_pixel_count, data, ANY),
                call(address_pixel_size, 1, ANY)]
        )

    def test_set_image_size_wrong_pixel(self, test_fem):

        test_fem.fem.set_image_size(102, 288, 0, 16)

        assert test_fem.fem.image_size_x == 102
        assert test_fem.fem.image_size_y == 288
        assert test_fem.fem.image_size_p == 0
        assert test_fem.fem.image_size_f == 16

        assert not test_fem.fem.x10g_rdma.write.called

    def test_load_vectors(self, test_fem):
        """Test the load vectors method writes the vector information via RDMA correctly"""
        test_fem.fem.load_vectors_from_file()

        test_fem.fem.x10g_rdma.write.assert_has_calls(test_fem.load_vectors_call_list)

    def test_frame_gate_settings(self, test_fem):
        frame_num = 10
        frame_gap = 1000
        test_fem.fem.frame_gate_settings(frame_num, frame_gap)

        test_fem.fem.x10g_rdma.write.assert_has_calls([
            call(test_fem.rdma_addr['frm_gate'] + 1, frame_num, ANY),
            call(test_fem.rdma_addr['frm_gate'] + 2, frame_gap, ANY)
        ])

    def test_frame_gate_trigger(self, test_fem):

        test_fem.fem.frame_gate_trigger()

        test_fem.fem.x10g_rdma.write.assert_has_calls([
            call(test_fem.rdma_addr['frm_gate'], 0, ANY),
            call(test_fem.rdma_addr['frm_gate'], 1, ANY)
        ])

    def test_cleanup(self, test_fem):
        test_fem.fem.cleanup()

        test_fem.fem.x10g_rdma.close.assert_called_with()
