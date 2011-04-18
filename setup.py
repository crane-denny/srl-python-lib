import os.path, sys

from distribute_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

import srllib

extra_kwds = {}
setup(name="srllib",
        version=srllib.__version__,
        author="Arve Knudsen",
        author_email="arve.knudsen@gmail.com",
        url="http://code.google.com/p/srl-python-lib",
        license=srllib.__license__,
        packages=find_packages(exclude=["Tests"]),
        **extra_kwds)
