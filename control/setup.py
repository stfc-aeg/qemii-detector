"""Setup script for odin_workshop python package."""

import sys
from setuptools import setup, find_packages
import versioneer

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(name='FileInterface',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='QEM Plugin/adapters for ODIN Framework',
      url='https://github.com/stfc-aeg/qemii-detector',
      author='Adam Neaves',
      author_email='adam.neaves@stfc.ac.uk',
      packages=find_packages(),
      install_requires=required,
      dependency_links=['https://github.com/odin-detector/odin-control/zipball/0.9.0#egg=odin'],
      zip_safe=False,
)
