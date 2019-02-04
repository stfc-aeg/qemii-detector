/*
 * QemiiProcessPlugin.cpp
 *
 *  Created on: 6 Jun 2016
 *      Author: gnx91527
 */

#include <QemiiProcessPlugin.h>
#include "version.h"
namespace FrameProcessor
{

  const std::string QemiiProcessPlugin::CONFIG_DROPPED_PACKETS = "packets_lost";
  const std::string QemiiProcessPlugin::CONFIG_ASIC_COUNTER_DEPTH = "bitdepth";
  const std::string QemiiProcessPlugin::CONFIG_IMAGE_WIDTH = "width";
  const std::string QemiiProcessPlugin::CONFIG_IMAGE_HEIGHT = "height";
  const std::string QemiiProcessPlugin::BIT_DEPTH[2] = {"12-bit", "24-bit"};

  /**
   * The constructor sets up logging used within the class.
   */
  QemiiProcessPlugin::QemiiProcessPlugin() :
      asic_counter_depth_(DEPTH_12_BIT),
      image_width_(Qemii::qemi_image_width),
      image_height_(Qemii::qemi_image_height),
      image_pixels_(Qemii::qemi_image_pixels),
      total_packets_lost_(0)
  {
    // Setup logging for the class
    logger_ = Logger::getLogger("FP.QemiiProcessPlugin");
    logger_->setLevel(Level::getAll());
    LOG4CXX_INFO(logger_, "QemiiProcessPlugin version " << this->get_version_long() << " loaded");
  }

  /**
   * Destructor.
   */
  QemiiProcessPlugin::~QemiiProcessPlugin()
  {
  }

  
  int QemiiProcessPlugin::get_version_major()
  {
    return ODIN_DATA_VERSION_MAJOR;
  }

 
  int QemiiProcessPlugin::get_version_minor()
  {
    return ODIN_DATA_VERSION_MINOR;
  }

 
  int QemiiProcessPlugin::get_version_patch()
  {
    return ODIN_DATA_VERSION_PATCH;
  }

  
  std::string QemiiProcessPlugin::get_version_short()
  {
    return ODIN_DATA_VERSION_STR_SHORT;
  }

  
  std::string QemiiProcessPlugin::get_version_long()
  {
    return ODIN_DATA_VERSION_STR;
  }

  
  void QemiiProcessPlugin::configure(OdinData::IpcMessage& config, OdinData::IpcMessage& reply)
  {
    if (config.has_param(QemiiProcessPlugin::CONFIG_DROPPED_PACKETS))
    {
      packets_lost_ = config.get_param<int>(QemiiProcessPlugin::CONFIG_DROPPED_PACKETS);
    }

    
    if (config.has_param(QemiiProcessPlugin::CONFIG_ASIC_COUNTER_DEPTH))
    {
      std::string bit_depth_str =
          config.get_param<std::string>(QemiiProcessPlugin::CONFIG_ASIC_COUNTER_DEPTH);
      /*
      if (bit_depth_str == BIT_DEPTH[DEPTH_1_BIT])
      {
        asic_counter_depth_ = DEPTH_1_BIT;
      }
      else if (bit_depth_str == BIT_DEPTH[DEPTH_6_BIT])
      {
        asic_counter_depth_ = DEPTH_6_BIT;
      }
      else if (bit_depth_str == BIT_DEPTH[DEPTH_12_BIT])
      {
        asic_counter_depth_ = DEPTH_12_BIT;
      }
      else if (bit_depth_str == BIT_DEPTH[DEPTH_24_BIT])
      {
        asic_counter_depth_ = DEPTH_24_BIT;
      }
      else
      {
        std::stringstream ss;
        ss << "Invalid bit depth requested: " << bit_depth_str;
        LOG4CXX_ERROR(logger_, "Invalid bit depth requested: " << bit_depth_str);
        throw std::runtime_error("Invalid bit depth requested");
      }
      */
    }

    else{

      asic_counter_depth_ = Qemii::QEMI_BIT_DEPTH;
    }
    

    if (config.has_param(QemiiProcessPlugin::CONFIG_IMAGE_WIDTH))
    {
      image_width_ = config.get_param<int>(QemiiProcessPlugin::CONFIG_IMAGE_WIDTH);
    }

    if (config.has_param(QemiiProcessPlugin::CONFIG_IMAGE_HEIGHT))
    {
      image_height_ = config.get_param<int>(QemiiProcessPlugin::CONFIG_IMAGE_HEIGHT);
    }

    image_pixels_ = image_width_ * image_height_;

  }

  
  void QemiiProcessPlugin::status(OdinData::IpcMessage& status)
  {
    // Record the plugin's status items
    LOG4CXX_INFO(logger_, "Status requested for Qemii plugin");
    status.set_param(get_name() + "/bitdepth", BIT_DEPTH[asic_counter_depth_]);
    status.set_param(get_name() + "/packets_lost", packets_lost_);
  }

 
  bool QemiiProcessPlugin::reset_statistics(void)
  {
    LOG4CXX_INFO(logger_, "Statistics reset requested for Qemii plugin")
    
    // Reset packets lost counter
    packets_lost_ = 0;

    return true;
  }

  
  boost shared_ptr<Frame> QemiiProcessPlugin::process_lost_packets(boost::shared_ptr<Frame> frame)
  {

    Qemii::FrameHeader* frame_header_ptr = reinterpret_cast<Qemii::FrameHeader*>(Frame->get_data());

    LOG4CXX_INFO(logger_, "Processing lost packets for Frame :" << frame_header_ptr->frame_number);
    LOG4CXX_INFO(logger_, "Received: " << frame_header_ptr->total_packets_received
                        << " out of a maximum " << Qemii::num_frame_packets << " packets.");


    if(frame_header_ptr->total_packets_received < (Qemii::num_frame_packets * (int)frame_header_ptr->num_active_fems)){


      size_t num_bytes = frame->get_data_size();
      void* image = (void*)malloc(num_bytes);
      memcpy(image, frame->get_data(), num_bytes);

      int num_packets_lost = (Qemii::num_frame_packets * (int)frame_header_ptr->num_active_fems) - frame_header_ptr->total_packets_received);
      
      total_packets_lost_ += num_packets_lost;
      LOG4CXX_INFO(logger_, "Lost a total of : " << total_packets_lost_ << "since starting.");

      // go over each active fem
      for(int fem = 0; fem < frame_header_ptr->num_active_fems; fem++){
        
        char* packet_ptr = (char*)image;
        packet_ptr += sizeof(Qemii::FrameHeader); // bypass the header in the buffer

        //loops over the number of packets
        for(int packet = 0; packet < Qemii::num_frame_packets; packet++){

          // check the packet state flag for this packet.
          if(frame_header_ptr->fem_rx_state[fem]->packet_state[packet] == 0){

            LOG4CXX_INFO(logger_, "missing packet nnumber : " << packet << " of Frame : " << frame_header_ptr->frame_number);

            memset(packet_ptr, 0, Qemii::payload_size); // set the packet data to 0's

          }
          //increment the ptr by the packet size for the next iteration
          packet_ptr += (Qemii::payload_size);
        }
       
      }

      checked_frame = boost::shared_ptr<Frame>(new Frame("Checked"))
      checked_frame->copy_data(image, num_bytes);
      free(image);

    }

    // return the frame with the 
    return checked_frame;
  }

 
  void QemiiProcessPlugin::process_frame(boost::shared_ptr<Frame> frame)
  {
    LOG4CXX_INFO(logger_, "Reordering frame.");
    LOG4CXX_INFO(logger_, "Frame size: " << frame->get_data_size());

    frame = this->process_lost_packets(frame);

    Qemii::FrameHeader* frame_header_ptr = reinterpret_cast<Qemii::FrameHeader*>(frame->get_data());

    LOG4CXX_INFO(logger_, "Processing Image for Frame Number: " << frame_header_ptr->frame_number);
    LOG4CXX_INFO(logger_, "Frame State: " << frame_header_ptr->frame_state);
    LOG4CXX_INFO(logger_, "Total Packets Received: " << frame_header_ptr->total_packets_received);
    LOG4CXX_INFO(logger_, "SOF's Seen : " << frame_header_ptr->total_sof_marker_count);
    LOG4CXX_INFO(logger_, "EOF's Seen : " << frame_header_ptr->total_eof_marker_count);
                            
    // get the size of the final image

    // allocate memory for that image size

    size_t image_size = reordered_image_size(QEMI_BIT_DEPTH);

    void* frame_data = static_cast<void*>(frame->get_data() + sizeof(Qemii::FrameHeader));

    //only one fem.. so this is all of the data.

  // Setup the frame dimensions and do a reshape.
    dimensions_t dimensions(2);
    dimensions[0] = image_height_;
    dimensions[1] = image_width_;

    boost::shared_ptr<Frame> the_frame = boost::shared_ptr<Frame>(new Frame("data"));

    the_frame->set_frame_number(frame_header_ptr->frame_number);
    data_frame->set_dimensions(dimensions);
    data_frame->copy_data(frame_data, output_image_size);

    LOG4CXX_TRACE(logger_, "Pushing data frame.");
    this->push(data_frame);

    free(frame_data);
    frame_data = NULL;

  }

 
  std::size_t QemiiProcessPlugin::reordered_image_size(int asic_counter_depth) {

    std::size_t image_size = 0;

    switch (asic_counter_depth)
    {
      case DEPTH_1_BIT:
      case DEPTH_6_BIT:
        image_size = image_width_ * image_height_ * sizeof(unsigned char);
        break;

      case DEPTH_12_BIT:
        image_size = image_width_ * image_height_ * sizeof(unsigned short);
        break;

      case DEPTH_24_BIT:
        image_size = image_width_ * image_height_ * sizeof(unsigned int);
        break;

      case QEMI_BIT_DEPTH:
        image_size = image_width_ * image_height_ * sizeof(uint16_t);

      default:
      {
        std::stringstream msg;
        msg << "Invalid bit depth specified for reordered slice size: " << asic_counter_depth;
        throw std::runtime_error(msg.str());
      }
      break;
    }

    return image_size;

  }


  void QemiiProcessPlugin::reorder_12bit_stripe(unsigned short* in, unsigned short* out,
      bool stripe_is_even)
  {

  }


  void QemiiProcessPlugin::reorder_16bit_stripe(unsigned short* in,
        unsigned int* out, bool stripe_is_even)
  {

  }


} /* namespace FrameProcessor */

