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
)
