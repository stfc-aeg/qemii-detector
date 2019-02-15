from setuptools import setup, find_packages
import versioneer

setup(
    name="qem",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='QEM Backplane plugin for ODIN framework',
    url='https://github.com/timcnicholls/odin',
    author='Tim Nicholls',
    author_email='tim.nicholls@stfc.ac.uk',
    packages=find_packages(),
    install_requires=['odin==0.2.0'],
    dependency_links = ['https://github.com/stfc-aeg/odin-control/zipball/0.2.0#egg=odin-0.2.0'],
    extras_require={
        'test': ['nose', 'coverage', 'mock']
    },
)
