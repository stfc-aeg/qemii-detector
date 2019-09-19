"""Setup script for odin_workshop python package."""

# import sys
from setuptools import setup, find_packages
import versioneer

required = [
    'tornado>4.3',
    'pyzmq>=17.0',
    'future',
    'psutil>5.0',
    'odin',
    'odin_devices'
]

dependency_links = [
    'https://github.com/odin-detector/odin-control/zipball/master#egg=odin',
    'https://github.com/stfc-aeg/odin-devices/zipball/device-copy#egg=odin_devices'  # replace when merged to master
]

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
