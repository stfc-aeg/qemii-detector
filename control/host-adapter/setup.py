from setuptools import setup, find_packages

setup(
    name="interface",
    description='QEM Interface plugin for ODIN framework',
    author='Ben Edwards',
    author_email='benjamin.edwards@stfc.ac.uk',
    packages=find_packages(),
    install_requires=['odin==0.2.0'],
    dependency_links = ['https://github.com/stfc-aeg/odin-control/zipball/0.2.0#egg=odin-0.2.0'],

)
