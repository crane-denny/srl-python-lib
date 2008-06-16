#!/usr/bin/env python
""" Generate code documentation with epydoc. """
import sys
import re
import os.path
import epydoc.cli

args = []
pkgs = []
re_arg = re.compile(r'(?:-[^-]+)|(?:--[^-])')
for a in sys.argv[1:]:
    if re_arg.match(a):
        args.append(a)
    else:
        pkgs.append(a)
pkgs = pkgs or ["srllib"]

doc_dir = os.path.join("Docs", "Epydoc")
if not os.path.exists(doc_dir):
    os.makedirs(doc_dir)
sys.argv = [sys.argv[0], "--html", "-o", doc_dir] + args + pkgs
epydoc.cli.cli()
