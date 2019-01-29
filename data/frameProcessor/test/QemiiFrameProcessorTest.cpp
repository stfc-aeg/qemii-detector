#define BOOST_TEST_MODULE "QEMIIFrameProcessorTests"
#define BOOST_TEST_MAIN
#include <boost/test/unit_test.hpp>
#include <boost/shared_ptr.hpp>

#include <iostream>

#include "QemiiProcessPlugin.h"
#include "DebugLevelLogger.h"

class QEMIIProcessPluginTestFixture
{
public:
	QEMIIProcessPluginTestFixture()
	{
		std::cout << "QEMIIProcessPluginTestFixture constructor" << std::endl;
	}

	~QEMIIProcessPluginTestFixture()
	{
		std::cout << "QEMIIProcessPluginTestFixture destructor" << std::endl;
	}
};

BOOST_FIXTURE_TEST_SUITE(QEMIIProcessPluginUnitTest, QEMIIProcessPluginTestFixture);

BOOST_AUTO_TEST_CASE(QEMIIProcessPluginTestFixture)
{
	std::cout << "QEMIIProcessPluginTestFixture test case" << std::endl;
}

BOOST_AUTO_TEST_SUITE_END();
