#!/usr/bin/env python
from __future__ import absolute_import

import sys, os.path

dpath = os.path.dirname(__file__)
if dpath:
    os.chdir(dpath)

sys.path.insert(0, os.path.realpath(os.path.pardir))
import srllib.testing
srllib.testing.run_tests("srllib")
