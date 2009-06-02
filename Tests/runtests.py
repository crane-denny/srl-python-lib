#!/usr/bin/env python

import sys, os.path

dpath = os.path.dirname(__file__)
if dpath:
    os.chdir(dpath)

sys.path.insert(0, os.path.pardir)
import srllib.testing
srllib.testing.run_tests("srllib")
