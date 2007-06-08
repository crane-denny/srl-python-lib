import os.path, sys
from distutils.core import setup

import srllib

extra_kwds = {}
setup(name="SRL Python Library", \
        version=srllib.__version__,
        author="Simula Research Laboratory", \
        license=srllib.__license__, \
        packages=["srllib"], \
        **extra_kwds
        )
