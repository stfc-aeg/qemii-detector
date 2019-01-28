/*
 * QEMIIDefinitions.h

 */

#ifndef INCLUDE_QEMIIDEFINITIONS_H_
#define INCLUDE_QEMIIDEFINITIONS_H_

namespace Qemii {

    static const size_t packet_size = 7352;
    static const size_t num_frame_packets = 8;
    static const size_t num_EOFS = 1;
    static const size_t num_SOFS = 1;
    static const size_t max_num_fems = 4;
    static const uint32_t EOF_marker = (64 << 24);// + 7;
    static const uint32_t SOF_marker = 128 << 24;
    static const uint32_t packet_num_mask = 0x3FFFFFFF;
    static const int32_t default_frame_number = -1;
    const std::string CONFIG_FEM_PORT_MAP = "fem_port_map";

    typedef struct
    {
        uint32_t frame_number;
        uint32_t packet_number;
    } PacketHeader;

    typedef struct
    {
      uint32_t packets_received;
      uint8_t  sof_marker_count;
      uint8_t  eof_marker_count;
      uint8_t  packet_state[num_frame_packets];
    } FemReceiveState;

    typedef struct
    {
        uint32_t frame_number;
        uint32_t frame_state; //incomplete/error/complete etc..
        struct timespec frame_start_time;
        uint32_t total_packets_received;
        uint8_t total_sof_marker_count;
        uint8_t total_eof_marker_count;
        uint8_t num_active_fems;
        uint8_t active_fem_idx[max_num_fems];
        FemReceiveState fem_rx_state[max_num_fems];
    } FrameHeader;


    inline const std::size_t max_frame_size(void)
    {
      std::size_t frame_size = (packet_size * num_frame_packets) * max_num_fems;
      return frame_size;
    }
}

#endif /* INCLUDE_QEMIIDEFINITIONS_H_ */
