/*
 * QemiiProcessPlugin.cpp
 *
 *  Created on: 6 Jun 2016
 *      Author: gnx91527
 * 
 * Updated 21/05/2020 - made changes to include frame_number to get round DAQ not resetting frame
 * number in header on new aquisition.  Also, configure function did not have the 2nd parameter
 * defined so base class was being called which does nothing
 * 
 */

#include <QemiiProcessPlugin.h>
#include "version.h"
namespace FrameProcessor
{

  const std::string QemiiProcessPlugin::CONFIG_DROPPED_PACKETS = "packets_lost";
  const std::string QemiiProcessPlugin::CONFIG_ASIC_COUNTER_DEPTH = "bitdepth";
  const std::string QemiiProcessPlugin::CONFIG_IMAGE_WIDTH = "width";
  const std::string QemiiProcessPlugin::CONFIG_IMAGE_HEIGHT = "height";
  const std::string QemiiProcessPlugin::BIT_DEPTH[2] = {"12-bit", "16-bit"};
  const std::string QemiiProcessPlugin::CONFIG_FRAME_NUMBER     = "frame_number";

  /**
   * The constructor sets up logging used within the class.
   */
  QemiiProcessPlugin::QemiiProcessPlugin() :
      asic_counter_depth_(Qemii::QEMI_BIT_DEPTH),
      image_width_(Qemii::qemii_image_width),
      image_height_(Qemii::qemii_image_height),
      image_pixels_(Qemii::qemii_image_pixels),
      frame_number_(0),
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

  /*
    Configure the frame processor 
    @param config: reference to an ipc config message with the parsed configuration params

    This method parses the configuration message updating the internal varibles with the 
    parameters to configure the processor. The total_packets_lost_, asic_counter_bit_depth_,
    image_width_ and image_hieght are all configured within this function.
  */
  void QemiiProcessPlugin::configure(OdinData::IpcMessage& config, OdinData::IpcMessage& reply)
  {
    if (config.has_param(QemiiProcessPlugin::CONFIG_DROPPED_PACKETS))
    {
      total_packets_lost_ = config.get_param<int>(QemiiProcessPlugin::CONFIG_DROPPED_PACKETS);
    }

    
    if (config.has_param(QemiiProcessPlugin::CONFIG_ASIC_COUNTER_DEPTH))
    {
      std::string bit_depth_str =
          config.get_param<std::string>(QemiiProcessPlugin::CONFIG_ASIC_COUNTER_DEPTH);

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
    if (config.has_param(QemiiProcessPlugin::CONFIG_FRAME_NUMBER))
    {
      frame_number_ = config.get_param<int>(QemiiProcessPlugin::CONFIG_FRAME_NUMBER);
      LOG4CXX_DEBUG(logger_, " QemiiProcessPlugin::configure - RESET frame_number to be " << frame_number_);
    }
    image_pixels_ = image_width_ * image_height_;

  }

  /*
    Gets the status of the frame processor. 
    @param status: reference to an ipc status message to hold the parameters in.
    This method populates the provided status message with the bitdepth and
    number of total packets lost for the current DAQ.
  */
  void QemiiProcessPlugin::status(OdinData::IpcMessage& status)
  {
    // Record the plugin's status items
    //LOG4CXX_INFO(logger_, "Status requested for Qemii plugin");
    status.set_param(get_name() + "/bitdepth", BIT_DEPTH[asic_counter_depth_]);
    status.set_param(get_name() + "/packets_lost", total_packets_lost_);
    status.set_param(get_name() + "/frame_number", frame_number_);
  }

  /*
    Reset the statistics for the frame processor.
    @return true.
    This method resets the total number of packets lost during a DAQ to 0.
  */
  bool QemiiProcessPlugin::reset_statistics(void)
  {
    LOG4CXX_INFO(logger_, "Statistics reset requested for Qemii plugin")
    
    // Reset packets lost counter
    total_packets_lost_ = 0;

    return true;
  }

  /*
    Process lost packets in a given QEM Frame.
    @param frame: shared pointer to a Frame object containing the raw frame data

    This method analyses the given frame to see if all expected packets have been
    received. If there are packets missing within the frame, the data for these packets 
    are zeroed out as the memory may contain data from a previous frame.
  */
  void QemiiProcessPlugin::process_lost_packets(boost::shared_ptr<Frame> frame)
  {

    boost::shared_ptr<Frame> checked_frame = frame;
    const Qemii::FrameHeader* frame_header_ptr = static_cast<const Qemii::FrameHeader*>(frame->get_data_ptr());
    uint16_t max_packets = (Qemii::num_frame_packets * (int)frame_header_ptr->num_active_fems);

    LOG4CXX_INFO(logger_, "Processing lost packets for Frame :" << frame_header_ptr->frame_number);
    LOG4CXX_INFO(logger_, "Received: " << frame_header_ptr->total_packets_received
                        << " out of a maximum " << max_packets << " packets.");


    if(frame_header_ptr->total_packets_received < max_packets){


      size_t num_bytes = frame->get_data_size();
      // void* image = (void*)malloc(num_bytes);
      // memcpy(image, frame->get_data(), num_bytes);

      int num_packets_lost = max_packets - frame_header_ptr->total_packets_received;
      
      total_packets_lost_ += num_packets_lost;
      LOG4CXX_INFO(logger_, "Lost a total of : " << total_packets_lost_ << "since starting.");
      

      // go over each active fem
      for(int fem = 0; fem < frame_header_ptr->num_active_fems; fem++){
        
        char* packet_ptr = static_cast<char *>(frame->get_data_ptr())+ sizeof(Qemii::FrameHeader); // bypass the header in the buffer

        //loops over the number of packets
        for(int packet = 0; packet < Qemii::num_frame_packets; packet++){

          // check the packet state flag for this packet.
          if(frame_header_ptr->fem_rx_state[fem].packet_state[packet] == 0){

            LOG4CXX_INFO(logger_, "missing packet number : " << packet << " of Frame : " << frame_header_ptr->frame_number);

            memset(packet_ptr, 0, Qemii::payload_size); // set the packet data to 0's

          }
          //increment the ptr by the packet size for the next iteration
          packet_ptr += (Qemii::payload_size);
        }
       
      }

    }

  }

  /*
    Process a QEM frame and release ready to be written to hdf5 as an image.
    @param frame: shread pointer to a Frame object holding the raw frame data.

    This method processes the incoming frame for lost packets and gets status information
    about the frame from the frame header. It calculates the image size and reshapes the frame data
    to fit the image width and height configured in the processor. 
    The frame is then copied and released to be processed by the rest of the processing chain.
  */

  void QemiiProcessPlugin::process_frame(boost::shared_ptr<Frame> frame)
  {
    LOG4CXX_INFO(logger_, "Reordering frame.");
    LOG4CXX_INFO(logger_, "Frame size: " << frame->get_data_size());


    const Qemii::FrameHeader* hdr_ptr = static_cast<const Qemii::FrameHeader*>(frame->get_data_ptr());

    LOG4CXX_INFO(logger_, "Processing Image for Frame Number: " << hdr_ptr->frame_number);
    LOG4CXX_INFO(logger_, "Frame State: " << hdr_ptr->frame_state);
    LOG4CXX_INFO(logger_, "Total Packets Received: " << hdr_ptr->total_packets_received);
    LOG4CXX_INFO(logger_, "SOF's Seen : " << (int)hdr_ptr->total_sof_marker_count);
    LOG4CXX_INFO(logger_, "EOF's Seen : " << (int)hdr_ptr->total_eof_marker_count);
                            
    // get the size of the final image

    // allocate memory for that image size

    size_t image_size = reordered_image_size(Qemii::QEMI_BIT_DEPTH);
    LOG4CXX_TRACE(logger_, "Output Image Size:   " << image_size);
    LOG4CXX_TRACE(logger_, "Output Image Height: " << image_height_);
    LOG4CXX_TRACE(logger_, "Output Image Width:  " << image_width_);


     // Loop over the active FEM list to determine the maximum active FEM index

    unsigned int max_active_fem_idx = 0;
    {
      std::stringstream msg;
      msg << "Number of active FEMs: " << static_cast<int>(hdr_ptr->num_active_fems) << " ids:";
      for (uint8_t idx = 0; idx < hdr_ptr->num_active_fems; idx++)
      {
        if (hdr_ptr->active_fem_idx[idx] > max_active_fem_idx)
        {
          max_active_fem_idx = hdr_ptr->active_fem_idx[idx];
        }
        msg << " " << static_cast<int>(hdr_ptr->active_fem_idx[idx]);
      }
      LOG4CXX_TRACE(logger_, msg.str());
    }

    this->process_lost_packets(frame);

  // Setup the frame dimensions and do a reshape.
    dimensions_t dimensions(2);
    dimensions[0] = image_height_;
    dimensions[1] = image_width_;

    FrameMetaData frame_meta;

    frame_meta.set_dataset_name("data");

    // Set frame metadata info
    frame_meta.set_compression_type(no_compression);
    
    frame_meta.set_frame_number(frame_number_); //
    
    //TODO: Interrim fix: (until F/W amended)
    //	Changes header's frame number.
    //hdr_ptr->frame_number = hdr_ptr->frame_number = frame_number_;

    frame_meta.set_dimensions(dimensions);
    frame_meta.set_data_type(raw_16bit);

    LOG4CXX_DEBUG(logger_, "CREATING DATABLOCKFRAME");
    boost::shared_ptr<Frame> data_frame = boost::shared_ptr<Frame>(new DataBlockFrame(frame_meta, image_size));

    //get pointers to input and output data ready for reordering
    const void* in_data_ptr = static_cast<const void*>(
        static_cast<const char*>(frame->get_data_ptr()) + sizeof(Qemii::FrameHeader)
    );
    const void* out_data_ptr = static_cast<const void*>(
        static_cast<const char*>(data_frame->get_data_ptr())
    );
    void* output_ptr = static_cast<void*>(static_cast<char*>(const_cast<void *>(out_data_ptr)));
    void* input_ptr = static_cast<void *>(static_cast<char*>(const_cast<void *>(in_data_ptr)));

    // for (uint8_t idx = 0; idx < hdr_ptr->num_active_fems; idx++)
    // {
    //   uint8_t fem_idx = hdr_ptr->active_fem_idx[idx];

    //   //calc pointer into input image based on fem index
    //   void* input_ptr = data_ptr + (idx * Qemii::payload_size);
    //   std::size_t output_offset = fem_idx * Qemii::payload_size;


    // }

    this->reorder_whole_image(static_cast<uint8_t *>(input_ptr), static_cast<uint16_t *>(output_ptr), image_height_*image_width_);

    LOG4CXX_DEBUG(logger_, "DATA FRAME METADATA: DATASET NAME" << frame_meta.get_dataset_name());
    LOG4CXX_TRACE(logger_, "Pushing data frame.");
    this->push(data_frame);
    // frame_data = NULL;
    // Manually update frame_number (until fixed in firmware)
    frame_number_++;

  }

 /*
  Calculate the size of a reordered image. 
  @param asic_counter_depth: integer value for the bitdepth used.
  @returns image_size: size_t object with the number of bytes in an image
  @throws runtime_error : if the bit depth provided is not recognised.
  This method caculates the image size using the provided bit depth, image width
  and image height that the processor is configured with. 
 */
  std::size_t QemiiProcessPlugin::reordered_image_size(int asic_counter_depth) {

    std::size_t image_size = 0;

    switch (asic_counter_depth)
    {
      case Qemii::QEMI_BIT_DEPTH:
        image_size = image_width_ * image_height_ * sizeof(uint16_t);
        break;
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
  
  /**
   * Reorder and unpack the pixel data
   * 
   * @param in - Pointer to incoming image data
   * @param out - Pointer to allocated memory for reordered image
   * @param num_pixels - the number of pixels. The reordered image will be this * 2 bytes large
   */
  void QemiiProcessPlugin::reorder_whole_image(uint8_t* in, uint16_t* out, size_t num_pixels) {
    // the pixels are 12 bit, and packed across byte boundries. They need to be unpacked to take 16 bits each
    uint16_t* end_out = out + num_pixels;
    int i = 0;
    // uint8_t byte_0, byte_1, byte_2;
    // byte_0 = 0;
    // byte_1 = 0;
    // byte_2 = 0;
    uint16_t pixel_0, pixel_1;
    
    LOG4CXX_DEBUG(logger_, "START PROCESSING")
    while(out < end_out)
    {
      // byte_0 = in[0];
      // byte_1 = in[1];
      // byte_2 = in[2];

      // std::cout << byte_0 << byte_1 << byte_2;

      // pixel_0 = ((in[1] & 0xF) << 8) + in[0];
      // pixel_1 = (in[1] >> 4) + (in[2] << 4);
      // LOG4CXX_DEBUG(logger_, "BYTES FROM INPUT: " << std::hex)
      out[0] = ((in[1] & 0xF) << 8) + in[0];
      out[1] = (in[1] >> 4) + (in[2] << 4);

      in += 3; //every 2 pixels is 3 bytes when packed, or two 16 bit words when unpacked
      out += 2; // does this increase by 2 16 bit words or by 2 bytes? unsure
      i++;
    }
    LOG4CXX_DEBUG(logger_, "number of loops = " << i)

    // std::memcpy(out, in, Qemii::qemii_image_pixels * 2);
  }
} /* namespace FrameProcessor */

