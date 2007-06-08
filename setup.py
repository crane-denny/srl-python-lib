import os.path, sys
from distutils.core import setup

import srllib

extra_kwds = {}
setup(name="SRL Python Library", version=srllib.__version__, author=
        "Simula Research Laboratory", author_email="arvenk@simula.no",
        license=srllib.__license__, packages=["srllib"], **extra_kwds)
