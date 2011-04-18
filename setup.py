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
        description="General Python application library.",
        platforms=["All"],
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Programming Language :: Python :: 2',
            'Operating System :: OS Independent',
            'Topic :: Software Development :: Libraries',
            ],
        packages=find_packages(exclude=["Tests"]),
        **extra_kwds)
