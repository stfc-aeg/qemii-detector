/*
 * QEMIIProcessPlugin.h
 *
 *  Created on: 6 Jun 2016
 *      Author: gnx91527
 */

#ifndef TOOLS_FILEWRITER_EXCALIBURREORDERPLUGIN_H_
#define TOOLS_FILEWRITER_EXCALIBURREORDERPLUGIN_H_

#include <log4cxx/logger.h>
#include <log4cxx/basicconfigurator.h>
#include <log4cxx/propertyconfigurator.h>
#include <log4cxx/helpers/exception.h>
using namespace log4cxx;
using namespace log4cxx::helpers;


#include "FrameProcessorPlugin.h"
#include "QemiiDefinitions.h"
#include "ClassLoader.h"
#include "DataBlockFrame.h"


namespace FrameProcessor
{

  /** Processing of Qemii Frame objects.
   *
   * The QemiiProcessPlugin class is currently responsible for receiving a raw data
   * Frame object and reordering the data into valid Qemii frames according to the selected
   * bit depth.
   */
  class QemiiProcessPlugin : public FrameProcessorPlugin
  {
  public:
    QemiiProcessPlugin();
    virtual ~QemiiProcessPlugin();
    
    int get_version_major();
    int get_version_minor();
    int get_version_patch();
    std::string get_version_short();
    std::string get_version_long();

    void configure(OdinData::IpcMessage& config);
    void status(OdinData::IpcMessage& status);
    bool reset_statistics(void);

  private:

    /** Configuration constant for clearing out dropped packet counters **/
    static const std::string CONFIG_DROPPED_PACKETS;
    /** Configuration constant for asic counter depth **/
    static const std::string CONFIG_ASIC_COUNTER_DEPTH;
    /** Configuration constant for image width **/
    static const std::string CONFIG_IMAGE_WIDTH;
    /** Configuration constant for image height **/
    static const std::string CONFIG_IMAGE_HEIGHT;
    static const std::string BIT_DEPTH[2];

    boost::shared_ptr<Frame> process_lost_packets(boost::shared_ptr<Frame> frame);
    void process_frame(boost::shared_ptr<Frame> frame);
    std::size_t reordered_image_size(int asic_counter_depth);

    /** Pointer to logger **/
    LoggerPtr logger_;
    /** Bit depth of the incoming frames **/
    int asic_counter_depth_;
    /** Image width **/
    int image_width_;
    /** Image height **/
    int image_height_;
    /** Image pixel count **/
    int image_pixels_;
    /** Packet loss counter **/
    int total_packets_lost_;
  };

  /**
   * Registration of this plugin through the ClassLoader.  This macro
   * registers the class without needing to worry about name mangling
   */
  REGISTER(FrameProcessorPlugin, QemiiProcessPlugin, "QemiiProcessPlugin");

} /* namespace FrameProcessor */

#endif /* TOOLS_FILEWRITER_EXCALIBURREORDERPLUGIN_H_ */
