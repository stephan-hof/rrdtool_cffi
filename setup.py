from setuptools import setup

with open('README.md') as fd:
    long_description = fd.read()

setup(
    name="rrdtool_cffi",
    version='0.1',
    description='Bindings for rrdtool via cffi',
    keywords='rrdtool cffi',
    author='Stephan Hofmockel',
    author_email="Use the github issues",
    url="https://github.com/stephan-hof/rrdtool_cffi",
    py_modules=['rrdtool_cffi'],
    install_requires=['cffi', 'six'],
    long_description=long_description,
)
