import os.path, sys

from distribute_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

import srllib

extra_kwds = {}
setup(name="SRL Python Library",
        version=srllib.__version__,
        author="Simula Research Laboratory",
        author_email="arvenk@simula.no",
        url="http://code.google.com/p/srl-python-lib",
        license=srllib.__license__,
        py_modules=["distribute_setup",],
        packages=find_packages(exclude=["Tests"]),
        **extra_kwds)
