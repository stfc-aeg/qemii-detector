#define BOOST_TEST_MODULE "QemiiFrameProcessorTests"
#define BOOST_TEST_MAIN
#include <boost/test/unit_test.hpp>
#include <boost/shared_ptr.hpp>

#include <iostream>

#include "QemiiProcessPlugin.h"
#include "DebugLevelLogger.h"

class QemiiProcessPluginTestFixture
{
public:
	QemiiProcessPluginTestFixture()
	{
		std::cout << "QemiiProcessPluginTestFixture constructor" << std::endl;
	}

	~QemiiProcessPluginTestFixture()
	{
		std::cout << "QemiiProcessPluginTestFixture destructor" << std::endl;
	}
};

BOOST_FIXTURE_TEST_SUITE(QemiiProcessPluginUnitTest, QemiiProcessPluginTestFixture);

BOOST_AUTO_TEST_CASE(QemiiProcessPluginTestFixture)
{
	std::cout << "QemiiProcessPluginTestFixture test case" << std::endl;
}

BOOST_AUTO_TEST_SUITE_END();
