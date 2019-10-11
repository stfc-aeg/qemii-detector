"""Setup script for odin_workshop python package."""

# import sys
from setuptools import setup, find_packages
import versioneer
import sys
PY3 = (sys.version_info[0] == 3)

required = [
    'odin',
    # 'odin_data',  # MANUAL INSTALL REQUIRED
    'odin_devices',
    'opencv-python'
]

if PY3:
    required.append("matplotlib")
else:
    required.append("tornado==4.5.3")
    required.append("matplotlib<=2.9.0")
    required.append("numpy<=1.16.5")

dependency_links = [
    'https://github.com/odin-detector/odin-control/zipball/master#egg=odin',
    'https://github.com/stfc-aeg/odin-devices/zipball/master#egg=odin_devices'
]
# subdirectory=tools/python&
setup(name='qemii',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='Odin Detector Adapters for QEMII',
      url='https://github.com/stfc-aeg/qemii-detector',
      author='Adam Neaves',
      author_email='adam.neaves@stfc.ac.uk',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      install_requires=required,
      dependency_links=dependency_links,
      zip_safe=False
      )
