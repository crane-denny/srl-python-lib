""" Test the signal module. """
import os.path

from srllib.testing import *
import srllib.process as _process
from _common import *

class ProcessTest(TestCase):
    def test_run_in_terminal(self):
        """ Test running code in virtual terminal. """
        import time
        def childfunc(prcs, outStr, errStr):
            import sys
            for i in range(10):
                sys.stdout.write("%s\n" % outStr)
                sys.stderr.write("%s\n" % errStr)

        if get_os_name() == Os_Linux:
            # Execute child function under supervision and observe outputs
            def slot_stdout(txt):
                self.__stdout += txt
            def slot_stderr(txt):
                self.__stderr += txt
            
            self.__stdout, self.__stderr = "", ""
            procmon = _process.ThreadedProcessMonitor(use_pty=True)
            self._connect_to(procmon.sig_stdout, slot_stdout)
            self._connect_to(procmon.sig_stderr, slot_stderr)
            
            procmon(childfunc, ["Test out", "Test err"])
            procmon.wait()

            for l in self.__stdout.splitlines():
                self.assertEqual(l, "Test out")
            for l in self.__stderr.splitlines():
                self.assertEqual(l, "Test err")