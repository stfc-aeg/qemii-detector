/*
 * QemiiCorrectionPlugin.cpp
 *
 *  Created on: 23 July 2019
 *      Author: Adam Neaves, Detector Systems Software Group
 */

#include "QemiiCorrectionPlugin.h"
#include "version.h"

namespace FrameProcessor
{

  const std::string QemiiCorrectionPlugin::CONFIG_CORRECTION_TYPE = "correction_type";
  const std::string QemiiCorrectionPlugin::CONFIG_OFFSET_VAL = "offset";
  const std::string QemiiCorrectionPlugin::CONFIG_COARSE_SCALE = "coarse_scale";
  const std::string QemiiCorrectionPlugin::CONFIG_FINE_SCALE = "fine_scale";
  /**
   * The constructor sets up logging used within the class.
   */
  QemiiCorrectionPlugin::QemiiCorrectionPlugin():
    correction_offset_(Qemii::qem_correction_offset),
    coarse_scale_(Qemii::qem_coarse_scale),
    fine_scale_(Qemii::qem_fine_scale),
    correction_type_(raw)
  {
    // Setup logging for the class
    logger_ = Logger::getLogger("FP.QemiiCorrectionPlugin");
    logger_->setLevel(Level::getAll());
    LOG4CXX_INFO(logger_, "QemiiCorrectionPlugin version " << this->get_version_long() << " loaded");
  }

/**
 * Destructor.
 */
QemiiCorrectionPlugin::~QemiiCorrectionPlugin()
{
  LOG4CXX_TRACE(logger_, "QemiiCorrectionPlugin destructor.");
}

/**
 * Perform processing on the frame. For the QemiiCorrectionPlugin class we are
 * simply going to log that we have received a frame.
 *
 * \param[in] frame - Pointer to a Frame object.
 */
void QemiiCorrectionPlugin::process_frame(boost::shared_ptr<Frame> frame)
{
  LOG4CXX_TRACE(logger_, "Received a new frame...");
  LOG4CXX_INFO(logger_, "Correcting Frame Number " << frame->get_frame_number());
  
  size_t data_size = frame->get_data_size();
  // uint16_t* new_data = (uint16_t*)malloc(data_size);
  // memcpy(new_data, frame->get_data_ptr(), data_size);
  FrameMetaData frame_meta = frame->get_meta_data();
  dimensions_t frame_dims = frame_meta.get_dimensions();
  int num_pixels = frame_dims[0] * frame_dims[1];
  boost::shared_ptr<Frame> new_frame = boost::shared_ptr<Frame>(new DataBlockFrame(frame_meta, data_size));
  if(correction_type_ == raw)
  {
    // if raw, just send the same data
    memcpy(new_frame->get_data_ptr(), frame->get_data_ptr(), data_size);
  }
  else
  {
    for(size_t i = 0; i<num_pixels; i++)
    {
      //get the current pixel from the original frame
      uint16_t pixel = static_cast<uint16_t*>(frame->get_data_ptr())[i];
      uint16_t coarse_val = (pixel & QEM_COARSE_MASK) >> 6;
      uint16_t fine_val   = (pixel & QEM_FINE_MASK);
      uint16_t corrected_val;

      switch(correction_type_)
      {
        case fine:
          corrected_val = fine_val;
          break;

        case coarse:
          corrected_val = coarse_val;
          break;

        case corrected:
          if(coarse_val < fine_val)
          {
            corrected_val = 0;
          }
          else
          {
            corrected_val = coarse_val - fine_val;
          }
          break;
        default:
         corrected_val = pixel;
      }

      static_cast<uint16_t*>(new_frame->get_data_ptr())[i] = corrected_val;

    }
  }
  LOG4CXX_TRACE(logger_, "Pushing Frame");
  this->push(new_frame);

}

void QemiiCorrectionPlugin::configure(OdinData::IpcMessage& config, OdinData::IpcMessage& reply)
{
  LOG4CXX_INFO(logger_, "Configuring Qemii Correction Plugin");
  if (config.has_param(CONFIG_CORRECTION_TYPE))
  {
    LOG4CXX_INFO(logger_, "Correction Type Configured");
    correction_type_ = get_correction_from_string(config.get_param<std::string>(CONFIG_CORRECTION_TYPE));
  }

  if (config.has_param(CONFIG_COARSE_SCALE))
  {
    LOG4CXX_INFO(logger_, "Coarse Scale Configured");
    coarse_scale_ = config.get_param<double>(CONFIG_COARSE_SCALE);
  }

  if(config.has_param(CONFIG_FINE_SCALE))
  {
    LOG4CXX_INFO(logger_, "Fine Scale Configured");
    fine_scale_ = config.get_param<double>(CONFIG_FINE_SCALE);
  }

  if(config.has_param(CONFIG_OFFSET_VAL))
  {
    LOG4CXX_INFO(logger_, "Correction Offset Configured");
    correction_offset_ = config.get_param<double>(CONFIG_OFFSET_VAL);
  }
}

void QemiiCorrectionPlugin::status(OdinData::IpcMessage& status)
  {
    // Record the plugin's status items
    //LOG4CXX_INFO(logger_, "Status requested for Qemii plugin");
    status.set_param(get_name() + "/type", get_string_from_correction(correction_type_));
    status.set_param(get_name() + "/coarse_scale", coarse_scale_);
    status.set_param(get_name() + "/fine_scale", fine_scale_);
    status.set_param(get_name() + "/offset", correction_offset_);
  }

int QemiiCorrectionPlugin::get_version_major()
{
  return ODIN_DATA_VERSION_MAJOR;
}

int QemiiCorrectionPlugin::get_version_minor()
{
  return ODIN_DATA_VERSION_MINOR;
}

int QemiiCorrectionPlugin::get_version_patch()
{
  return ODIN_DATA_VERSION_PATCH;
}

std::string QemiiCorrectionPlugin::get_version_short()
{
  return ODIN_DATA_VERSION_STR_SHORT;
}

std::string QemiiCorrectionPlugin::get_version_long()
{
  return ODIN_DATA_VERSION_STR;
}

} /* namespace FrameProcessor */
