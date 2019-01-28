
#include "QemiiFrameDecoder.h"
#include "logging.h"
#include "version.h"
#include "gettime.h"
#include <iostream>
#include <iomanip>
#include <sstream>
#include <string>
#include <arpa/inet.h>
#include <boost/algorithm/string.hpp>

using namespace FrameReceiver;

#define MAX_IGNORED_PACKET_REPORTS 10


QemiiFrameDecoder::QemiiFrameDecoder():
    FrameDecoderUDP(),
    current_frame_seen_(Qemii::default_frame_number),
    current_frame_buffer_id_(Qemii::default_frame_number),
    current_frame_buffer_(0),
    current_frame_header_(0),
    packets_ignored_(0),
    packets_lost_(0),
    dropping_frame_data_(false),
    num_active_fems_(0)
{

    current_packet_header_.reset(new uint8_t[sizeof(Qemii::PacketHeader)]);
    dropped_frame_buffer_.reset(new uint8_t[Qemii::max_frame_size()]);
    ignored_packet_buffer_.reset(new uint8_t[Qemii::packet_size]);
    this->logger_ = Logger::getLogger("FR.QemiiDecoderPlugin");
    LOG4CXX_INFO(logger_, "QemiiFrameDecoder version " << this->get_version_long() << " loaded");

}

//! Destructor for QemiiFrameDecoder
//!
QemiiFrameDecoder::~QemiiFrameDecoder()
{
}

int QemiiFrameDecoder::get_version_major()
{
  return ODIN_DATA_VERSION_MAJOR;
}

int QemiiFrameDecoder::get_version_minor()
{
  return ODIN_DATA_VERSION_MINOR;
}

int QemiiFrameDecoder::get_version_patch()
{
  return ODIN_DATA_VERSION_PATCH;
}

std::string QemiiFrameDecoder::get_version_short()
{
  return ODIN_DATA_VERSION_STR_SHORT;
}

std::string QemiiFrameDecoder::get_version_long()
{
  return ODIN_DATA_VERSION_STR;
}


void QemiiFrameDecoder::init(LoggerPtr& logger, OdinData::IpcMessage& config_msg){


    FrameDecoder::init(logger_, config_msg);

    LOG4CXX_DEBUG_LEVEL(2, logger_, "Got decoder config message: " << config_msg.encode());

    
    if(config_msg.has_param(Qemii::CONFIG_FEM_PORT_MAP)){

        fem_port_map_str_ = config_msg.get_param<std::string>(Qemii::CONFIG_FEM_PORT_MAP);
        LOG4CXX_DEBUG_LEVEL(1, logger_, "Parsing FEM to port map found in config: "
                          << fem_port_map_str_);
    }
    else{
        LOG4CXX_DEBUG_LEVEL(1,logger_, "No FEM to port map found in config, using default: "
                          << default_fem_port_map);
        fem_port_map_str_ = default_fem_port_map;
    }

    num_active_fems_ = parse_fem_port_map(fem_port_map_str_);

    if (num_active_fems_)  {
        LOG4CXX_DEBUG_LEVEL(1, logger_, "Parsed " << num_active_fems_
                            << " entries from port map configuration");
    }
    else
    {
        throw OdinData::OdinDataException("Failed to parse FEM to port map entries from configuration");
    }

    packets_ignored_ = 0;
    packets_lost_ = 0;

    for (int fem = 0; fem < Qemii::max_num_fems; fem++){
          fem_packets_lost_[fem] = 0;
    }
    
}


void QemiiFrameDecoder::request_configuration(const std::string param_prefix, OdinData::IpcMessage& config_reply){

  // Call the base class method to populate parameters
  FrameDecoder::request_configuration(param_prefix, config_reply);

  // Add current configuration parameters to reply
  config_reply.set_param(param_prefix + Qemii::CONFIG_FEM_PORT_MAP, fem_port_map_str_);

}

const size_t QemiiFrameDecoder::get_frame_buffer_size(void) const{

    size_t buffer_size = get_frame_header_size() + ((Qemii::packet_size * Qemii::num_frame_packets) * num_active_fems_);
    return buffer_size;
}

const size_t QemiiFrameDecoder::get_frame_header_size(void) const{

    return sizeof(Qemii::FrameHeader);
}

const size_t QemiiFrameDecoder::get_packet_header_size(void) const{

    return sizeof(Qemii::PacketHeader);

}

void QemiiFrameDecoder::process_packet_header (size_t bytes_received, int port,
                            struct sockaddr_in* from_addr){


    // Resolve the FEM index from the port the packet arrived on
    if (fem_port_map_.count(port)) {
        current_packet_fem_map_ =  fem_port_map_[port];

    }
    else{
        current_packet_fem_map_ = QemiiDecoderFemMapEntry(ILLEGAL_FEM_IDX, ILLEGAL_FEM_IDX);
        packets_ignored_++;
        
        if (packets_ignored_ < MAX_IGNORED_PACKET_REPORTS){
            LOG4CXX_WARN(logger_, "Ignoring packet received on port " << port << " for unknown FEM idx");
        }
        else if (packets_ignored_ == MAX_IGNORED_PACKET_REPORTS){
            LOG4CXX_WARN(logger_, "Reporting limit for ignored packets reached, suppressing further messages");
        }
    }

    // Extract fields from packet header
    uint32_t frame_number = get_frame_num();
    uint32_t packet_number = get_packet_num();
    bool start_of_frame_marker = get_sof_marker();
    bool end_of_frame_marker = get_eof_marker();

    
    LOG4CXX_DEBUG_LEVEL(3, logger_, "Got packet header:" << " packet: " << packet_number
        << " frame: " << frame_number
        << " SOF: " << (int) start_of_frame_marker
        << " EOF: " << (int) end_of_frame_marker
        << " port: " << port << " fem idx: " << current_packet_fem_map_.fem_idx_
    );
    

  // Only handle the packet header and frame logic further if this packet is not being ignored
  if (current_packet_fem_map_.fem_idx_ != ILLEGAL_FEM_IDX)
  {
    if (frame_number != current_frame_seen_)
    {
      current_frame_seen_ = frame_number;

      if (frame_buffer_map_.count(current_frame_seen_) == 0)
      {
        if (empty_buffer_queue_.empty())
        {
          current_frame_buffer_ = dropped_frame_buffer_.get();

          if (!dropping_frame_data_)
          {
            LOG4CXX_ERROR(logger_, "First packet from frame " << current_frame_seen_
                << " detected but no free buffers available. Dropping packet data for this frame");
            dropping_frame_data_ = true;
          }
        }
        else
        {

          current_frame_buffer_id_ = empty_buffer_queue_.front();
          empty_buffer_queue_.pop();
          frame_buffer_map_[current_frame_seen_] = current_frame_buffer_id_;
          current_frame_buffer_ = buffer_manager_->get_buffer_address(current_frame_buffer_id_);

          if (!dropping_frame_data_)
          {
            LOG4CXX_DEBUG_LEVEL(2, logger_, "First packet from frame " << current_frame_seen_
                << " detected, allocating frame buffer ID " << current_frame_buffer_id_);
          }
          else
          {
            dropping_frame_data_ = false;
            LOG4CXX_DEBUG_LEVEL(2, logger_, "Free buffer now available for frame "
                << current_frame_seen_ << ", allocating frame buffer ID "
                << current_frame_buffer_id_);
          }
        }

        // Initialise frame header
        current_frame_header_ = reinterpret_cast<Qemii::FrameHeader*>(current_frame_buffer_);
        initialise_frame_header(current_frame_header_);

      }
      else
      {
        current_frame_buffer_id_ = frame_buffer_map_[current_frame_seen_];
        current_frame_buffer_ = buffer_manager_->get_buffer_address(current_frame_buffer_id_);
        current_frame_header_ = reinterpret_cast<Qemii::FrameHeader*>(current_frame_buffer_);
      }

    }

    Qemii::FemReceiveState* fem_rx_state =
        &(current_frame_header_->fem_rx_state[current_packet_fem_map_.buf_idx_]);

    // If SOF or EOF markers seen in packet header, increment appropriate field in frame header
    if (start_of_frame_marker)
    {
      (fem_rx_state->sof_marker_count)++;
      (current_frame_header_->total_sof_marker_count)++;
    }
    if (end_of_frame_marker)
    {
      (fem_rx_state->sof_marker_count)++;
      (current_frame_header_->total_eof_marker_count)++;
    }

    // Update packet_number state map in frame header
    fem_rx_state->packet_state[packet_number] = 1;
  }


}

void QemiiFrameDecoder::get_status(const std::string param_prefix, OdinData::IpcMessage& status_msg){
  
  status_msg.set_param(param_prefix + "name", std::string("QemiiFrameDecoder"));
  status_msg.set_param(param_prefix + "packets_lost", packets_lost_);
  status_msg.set_param(param_prefix + "packets_ignored", packets_ignored_);

  // Workaround for lack of array setters in IpcMessage
  rapidjson::Value fem_packets_lost_array(rapidjson::kArrayType);
  rapidjson::Value::AllocatorType allocator;

  for (int fem = 0; fem < Qemii::max_num_fems; fem++)
  {
    fem_packets_lost_array.PushBack(fem_packets_lost_[fem], allocator);
  }
  status_msg.set_param(param_prefix + "fem_packets_lost", fem_packets_lost_array);


}


void* QemiiFrameDecoder::get_packet_header_buffer(void){

    return current_packet_header_.get();
}

void* QemiiFrameDecoder::get_next_payload_buffer(void) const{

  uint8_t* next_receive_location;

  if (current_packet_fem_map_.fem_idx_ != ILLEGAL_FEM_IDX)
  {

    next_receive_location = reinterpret_cast<uint8_t*>(current_frame_buffer_)
          + get_frame_header_size ()
          + (Qemii::packet_size * get_packet_num());
  }
  else
  {
    next_receive_location = reinterpret_cast<uint8_t*>(ignored_packet_buffer_.get());
  }

  return reinterpret_cast<void*>(next_receive_location);
}


FrameDecoder::FrameReceiveState QemiiFrameDecoder::process_packet(
    size_t bytes_received, int port, struct sockaddr_in* from_addr){


    FrameDecoder::FrameReceiveState frame_state = FrameDecoder::FrameReceiveStateIncomplete;

    // Only process the packet if it is not being ignored due to an illegal port to FEM index mapping
    if (current_packet_fem_map_.fem_idx_ != ILLEGAL_FEM_IDX)
    {

    // If this packet is the last in subframe (i.e. has on EOF marker in the header), extract the
    // frame number (which counts from 1) from the subframe trailer where present, update and/or
    // validate in the frame buffer header appropriately.
    /*
    if (get_end_of_frame_marker())
    {
      
        uint32_t frame_number;
        //uint32_t subframe_idx = get_subframe_counter() % num_subframes_;

        size_t payload_bytes_received = bytes_received - sizeof(Qemii::PacketHeader);

        // do I need to do frame number validation? 

        Excalibur::SubframeTrailer* trailer =
            reinterpret_cast<Excalibur::SubframeTrailer*>((uint8_t*) get_next_payload_buffer()
                + payload_bytes_received - sizeof(Excalibur::SubframeTrailer));

        frame_number = static_cast<uint32_t>((trailer->frame_number & 0xFFFFFFFF) - 1);
        LOG4CXX_DEBUG_LEVEL(3, logger_, "Subframe EOF trailer FEM: "
            << current_packet_fem_map_.fem_idx_ << " subframe_idx: " << subframe_idx
            << " frame: " << frame_number
            << " current frame: " << current_frame_header_->frame_number);

    }
    */

    // Get a convenience pointer to the FEM receive state data in the frame header
    Qemii::FemReceiveState* fem_rx_state =
        &(current_frame_header_->fem_rx_state[current_packet_fem_map_.buf_idx_]);

    // Increment the total and per-FEM packet received counters
    (fem_rx_state->packets_received)++;
    current_frame_header_->total_packets_received++;

    // If we have received the expected number of packets, perform end of frame processing
    // and hand off the frame for downstream processing.
    if (current_frame_header_->total_packets_received == Qemii::num_frame_packets)
    {

      // Check that the appropriate number of SOF and EOF markers (one each per subframe) have
      // been seen, otherwise log a warning

      if ((current_frame_header_->total_sof_marker_count != num_active_fems_)||
          (current_frame_header_->total_eof_marker_count != num_active_fems_))
      {
        LOG4CXX_WARN(logger_, "Incorrect number of SOF ("
           << (int)current_frame_header_->total_sof_marker_count << ") or EOF ("
           << (int)current_frame_header_->total_eof_marker_count << ") markers "
           << "seen on completed frame " << current_frame_seen_);
      }

      // Set frame state accordingly
      frame_state = FrameDecoder::FrameReceiveStateComplete;

      // Complete frame header
      current_frame_header_->frame_state = frame_state;

      if (!dropping_frame_data_)
      {
        // Erase frame from buffer map
        frame_buffer_map_.erase(current_frame_seen_);

        // Notify main thread that frame is ready
        ready_callback_(current_frame_buffer_id_, current_frame_header_->frame_number);

        // Reset current frame seen ID so that if next frame has same number (e.g. repeated
        // sends of single frame 0), it is detected properly
        current_frame_seen_ = -1;
      }
    }
  }
  return frame_state;

}

void QemiiFrameDecoder::monitor_buffers(void){

    int frames_timedout = 0;
    struct timespec current_time;

    gettime(&current_time);

    // Loop over frame buffers currently in map and check their state
    std::map<int, int>::iterator buffer_map_iter = frame_buffer_map_.begin();
    while (buffer_map_iter != frame_buffer_map_.end())
    {
        int frame_num = buffer_map_iter->first;
        int buffer_id = buffer_map_iter->second;
        void* buffer_addr = buffer_manager_->get_buffer_address(buffer_id);
        Qemii::FrameHeader* frame_header = reinterpret_cast<Qemii::FrameHeader*>(buffer_addr);

        if (elapsed_ms(frame_header->frame_start_time, current_time) > frame_timeout_ms_)
        {
            // Calculate packets lost on this frame and add to total
            uint32_t packets_lost = (Qemii::num_frame_packets * num_active_fems_) -
                frame_header->total_packets_received;
            packets_lost_ += packets_lost;

            if (packets_lost)
            {
                for (QemiiDecoderFemMap::iterator iter = fem_port_map_.begin();
                    iter != fem_port_map_.end(); ++iter)
                {
                fem_packets_lost_[(iter->second).fem_idx_] += Qemii::num_frame_packets -
                    (frame_header->fem_rx_state[(iter->second).buf_idx_].packets_received);
                }
            }

            LOG4CXX_DEBUG_LEVEL(1, logger_, "Frame " << frame_num << " in buffer " << buffer_id
                << " addr 0x" << std::hex
                << buffer_addr << std::dec << " timed out with " << frame_header->total_packets_received
                << " packets received, " << packets_lost << " packets lost");

            frame_header->frame_state = FrameReceiveStateTimedout;
            ready_callback_(buffer_id, frame_num);
            frames_timedout++;

            frame_buffer_map_.erase(buffer_map_iter++);
        }
        else
        {
            buffer_map_iter++;
        }
    }
    if (frames_timedout)
    {
        LOG4CXX_WARN(logger_, "Released " << frames_timedout << " timed out incomplete frames");
    }

    frames_timedout_ += frames_timedout;

    LOG4CXX_DEBUG_LEVEL(4, logger_,  get_num_mapped_buffers() << " frame buffers in use, "
        << get_num_empty_buffers() << " empty buffers available, "
        << frames_timedout_ << " incomplete frames timed out, "
        << packets_lost_ << " packets lost"
    );

}

void QemiiFrameDecoder::initialise_frame_header(Qemii::FrameHeader* header_ptr){
    
    header_ptr->frame_number = current_frame_seen_;
    header_ptr->frame_state = FrameDecoder::FrameReceiveStateIncomplete;
    header_ptr->total_packets_received = 0;
    header_ptr->total_sof_marker_count = 0;
    header_ptr->total_eof_marker_count = 0;
    header_ptr->num_active_fems = num_active_fems_;

    for (QemiiDecoderFemMap::iterator it = fem_port_map_.begin();
            it != fem_port_map_.end(); ++it)
    {
        header_ptr->active_fem_idx[(it->second).buf_idx_] = (it->second).fem_idx_;
    }

    memset(header_ptr->fem_rx_state, 0,
      sizeof(Qemii::FemReceiveState) * Qemii::max_num_fems);

    gettime(reinterpret_cast<struct timespec*>(&(header_ptr->frame_start_time)));


}

unsigned int QemiiFrameDecoder::elapsed_ms(struct timespec& start, struct timespec& end)
{

  double start_ns = ((double) start.tv_sec * 1000000000) + start.tv_nsec;
  double end_ns = ((double) end.tv_sec * 1000000000) + end.tv_nsec;

  return (unsigned int)((end_ns - start_ns) / 1000000);
}


void QemiiFrameDecoder::reset_statistics(void){

      // Call the base class reset method
    FrameDecoderUDP::reset_statistics();

    LOG4CXX_DEBUG_LEVEL(1, logger_, "Resetting QemiiFrameDecoder statistics");


  // Reset the scratched and lost packet counters
  packets_ignored_ = 0;
  packets_lost_ = 0 ;
  for (int fem = 0; fem < Qemii::max_num_fems; fem++)
  {
    fem_packets_lost_[fem] = 0;
  }
}

size_t QemiiFrameDecoder::get_next_payload_size(void) const
{
  
  return Qemii::packet_size;
}

bool QemiiFrameDecoder::get_eof_marker(void) const{

    uint32_t packet_number = reinterpret_cast<Qemii::PacketHeader*>(
        current_packet_header_.get())->packet_number;
    return ((packet_number & Qemii::EOF_marker) != 0);
}
bool QemiiFrameDecoder::get_sof_marker(void) const {

    uint32_t packet_number = reinterpret_cast<Qemii::PacketHeader*>(
        current_packet_header_.get())->packet_number;
    return ((packet_number & Qemii::SOF_marker) != 0); 
}

uint32_t QemiiFrameDecoder::get_packet_num(void) const{

  return reinterpret_cast<Qemii::PacketHeader*>(
      current_packet_header_.get())->packet_number & Qemii::packet_num_mask;
}

uint32_t QemiiFrameDecoder::get_frame_num(void) const{
    return reinterpret_cast<Qemii::PacketHeader*>(current_packet_header_.get())->frame_number;
}

int QemiiFrameDecoder::parse_fem_port_map(std::string& fem_port_map){

    // Define entry and port:idx delimiters
    const std::string entry_delimiter(",");
    const std::string elem_delimiter(":");

    // Vector to hold entries split from map
    std::vector<std::string> map_entries;

    // Split into entries
    boost::split(map_entries, fem_port_map, boost::is_any_of(entry_delimiter));

    unsigned int buf_idx = 0;
    // Loop over entries, further splitting into port / fem index pairs
    for (std::vector<std::string>::iterator it = map_entries.begin(); it != map_entries.end(); ++it)
    {
        if (buf_idx >= Qemii::max_num_fems) {
          LOG4CXX_WARN(logger_, "Decoder FEM port map configuration contains too many elements, "
                        << "truncating to maximium number of FEMs allowed ("
                        << Qemii::max_num_fems << ")");
          break;
        }

        std::vector<std::string> entry_elems;
        boost::split(entry_elems, *it, boost::is_any_of(elem_delimiter));

        // If a valid entry is found, save into the map
        if (entry_elems.size() == 2) {
            int port = static_cast<int>(strtol(entry_elems[0].c_str(), NULL, 10));
            int fem_idx = static_cast<int>(strtol(entry_elems[1].c_str(), NULL, 10));
            fem_port_map_[port] = QemiiDecoderFemMapEntry(fem_idx, buf_idx);
            buf_idx++;
        }
    }

    // Return the number of valid entries parsed
    return fem_port_map_.size();

}