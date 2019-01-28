
#ifndef INCLUDE_QEMIIFRAMEDECODER_H_
#define INCLUDE_QEMIIFRAMEDECODER_H_

#include "FrameDecoderUDP.h"
#include "QemiiDefinitions.h"
#include <iostream>
#include <map>
#include <stdint.h>
#include <time.h>

#define ILLEGAL_FEM_IDX -1

namespace FrameReceiver
{

  const std::string default_fem_port_map = "51501:0";

    typedef struct QemiiDecoderFemMapEntry
  {
    int fem_idx_;
    unsigned int buf_idx_;

    QemiiDecoderFemMapEntry(int fem_idx=ILLEGAL_FEM_IDX, int buf_idx=ILLEGAL_FEM_IDX) :
      fem_idx_(fem_idx),
      buf_idx_(buf_idx)
    {};
  } QemiiDecoderFemMapEntry;

  typedef std::map<int, QemiiDecoderFemMapEntry> QemiiDecoderFemMap;
 
  class QemiiFrameDecoder : public FrameDecoderUDP
  {
  public:

    QemiiFrameDecoder();
    ~QemiiFrameDecoder();

    int get_version_major();
    int get_version_minor();
    int get_version_patch();
    std::string get_version_short();
    std::string get_version_long();

    void init(LoggerPtr& logger, OdinData::IpcMessage& config_msg);
    void request_configuration(const std::string param_prefix, OdinData::IpcMessage& config_reply);

    const size_t get_frame_buffer_size(void) const;
    const size_t get_frame_header_size(void) const;

    inline const bool requires_header_peek(void) const
    {
      return true;
    };

    void get_status(const std::string param_prefix, OdinData::IpcMessage& status_msg);
    const size_t get_packet_header_size(void) const;
    void process_packet_header (size_t bytes_received, int port,
                                struct sockaddr_in* from_addr);
    void* get_packet_header_buffer(void);
    void* get_next_payload_buffer(void) const;
    size_t get_next_payload_size(void) const;
    
    FrameDecoder::FrameReceiveState process_packet(
      size_t bytes_received, int port, struct sockaddr_in* from_addr);

    void monitor_buffers(void);
 

    bool get_eof_marker(void) const;
    bool get_sof_marker(void) const;
    uint32_t get_packet_num(void) const;
    uint32_t get_frame_num(void) const;

    void reset_stats(void);
    unsigned int elapsed_ms(struct timespec& start, struct timespec& end);
    int parse_fem_port_map(std::string& port_map);

    private:

      void initialise_frame_header(Qemii::FrameHeader* header_ptr);

      QemiiDecoderFemMap fem_port_map_;
      std::string fem_port_map_str_;
      boost::shared_ptr<void> current_packet_header_;
      boost::shared_ptr<void> dropped_frame_buffer_;
      boost::shared_ptr<void> ignored_packet_buffer_;
      bool dropping_frame_data_;
      uint32_t current_frame_seen_;
      int current_frame_buffer_id_;
      void* current_frame_buffer_;
      
      Qemii::FrameHeader* current_frame_header_;
      QemiiDecoderFemMapEntry current_packet_fem_map_;
      std::size_t num_active_fems_;


      uint32_t packets_ignored_;
      uint32_t packets_lost_;
      uint32_t fem_packets_lost_[Qemii::max_num_fems];
  };

} // namespace FrameReceiver

#endif /* INCLUDE_QEMIIFRAMEDECODER_H_ */
