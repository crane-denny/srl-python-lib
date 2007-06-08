#!/usr/bin/env python

import sys, os.path

sys.path.insert(0, os.path.pardir)
import srllib.testing
srllib.testing.run_tests("srllib")
