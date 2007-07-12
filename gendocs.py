#!/usr/bin/env python
""" Generate code documentation with epydoc. """
import epydoc.cli, sys, re

args = []
pkgs = []
re_arg = re.compile(r'(?:-[^-]+)|(?:--[^-])')
for a in sys.argv[1:]:
    if re_arg.match(a):
        args.append(a)
    else:
        pkgs.append(a)
pkgs = pkgs or ["srllib"]

sys.argv = [sys.argv[0], "--html", "-o", "Docs/Epydoc"] + args + pkgs
epydoc.cli.cli()
