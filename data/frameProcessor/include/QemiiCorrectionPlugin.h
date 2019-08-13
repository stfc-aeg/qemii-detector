/*
 * QemiiCorrectionPlugin.h 
 * 
 *  Created on: 23 July 2019
 *      Author: Adam Neaves, Detector Systems Software Group
 */

#ifndef QEMII_CORRECTION_PLUGIN_H_
#define QEMII_CORRECTION_PLUGIN_H_

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

#define QEM_COARSE_MASK 0x07c0
#define QEM_FINE_MASK 0x003f

namespace FrameProcessor
{
    /** Correcting the Qemii Frame's based off coarse/fine values
     * 
     * The QemiiCorrectionPlugin class is responsible for applying corrections
     * to the raw data
     * 
     */
    class QemiiCorrectionPlugin : public FrameProcessorPlugin
    {
    public:
        
        enum CorrectionType
        {
            raw,
            coarse,
            fine,
            corrected
        };

        static CorrectionType get_correction_from_string(const std::string &str)
        {
            if(str == "raw")
                return raw;
            else if(str == "coarse")
                return coarse;
            else if(str == "fine")
                return fine;
            else if(str == "corrected")
                return corrected;
            return raw;
        }

        static std::string get_string_from_correction(CorrectionType correction)
        {
            switch(correction)
            {
                case raw:
                    return "raw";
                case coarse:
                    return "coarse";
                case fine:
                    return "fine";
                case corrected:
                    return "corrected";
                default:
                    return "raw";
            }
        }

        static const std::string CONFIG_CORRECTION_TYPE;
        static const std::string CONFIG_OFFSET_VAL;
        static const std::string CONFIG_COARSE_SCALE;
        static const std::string CONFIG_FINE_SCALE;

        QemiiCorrectionPlugin();
        virtual ~QemiiCorrectionPlugin();

        int get_version_major();
        int get_version_minor();
        int get_version_patch();
        std::string get_version_short();
        std::string get_version_long();

        void configure(OdinData::IpcMessage& config, OdinData::IpcMessage& reply);
        void status(OdinData::IpcMessage& status);

    private:

        void process_frame(boost::shared_ptr<Frame> frame);
 
        /** Pointer to Logger **/
        LoggerPtr logger_;
        
        CorrectionType correction_type_;
        double correction_offset_;
        double coarse_scale_;
        double fine_scale_;
    };

    /**
   * Registration of this plugin through the ClassLoader.  This macro
   * registers the class without needing to worry about name mangling
   */
  REGISTER(FrameProcessorPlugin, QemiiCorrectionPlugin, "QemiiCorrectionPlugin");
}

#endif /*QEMII_CORRECTION_PLUGIN_H_ */