""" Test the signal module. """
import os.path, time

from srllib.testing import *
import srllib.process as _process
from _common import *

class TestError(_process.PickleableException):
    pass

class ProcessTest(TestCase):
    def test_child_exception(self):
        """ Test catching an exception raised in the child. """
        
        def childfunc(process):
            raise TestError("Error in child")
        proc = _process.Process(childfunc)
        try: proc.wait()
        except _process.ChildError, err:            
            self.assert_(isinstance(err.orig_exception, TestError))
                
    def test_run_in_terminal(self):
        """ Test running code in virtual terminal. """
        import time
        def childfunc(prcs, outstr, errstr):
            import sys
            for i in range(10):
                sys.stdout.write("%s\n" % outstr)
                sys.stderr.write("%s\n" % errstr)

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
                
class ThreadedProcessMonitorTest(TestCase):
    """ Test the threaded process monitor. """
    def test_capture_output(self):
        """ Test capturing textual output from child process. """
        def slot_stdout(text):
            self.__stdout += text
        def slot_stderr(text):
            self.__stderr += text
            
        def childfunc(process):
            import sys
            sys.stdout.write("Test stdout")
            sys.stderr.write("Test stderr"    )
            
        procmon = _process.ThreadedProcessMonitor()
        self.__stdout, self.__stderr = "", ""
        self._connect_to(procmon.sig_stdout, slot_stdout)
        self._connect_to(procmon.sig_stderr, slot_stderr)
        procmon(childfunc)
        procmon.wait()
        self.assertEqual(self.__stdout, "Test stdout")
        self.assertEqual(self.__stderr, "Test stderr")
    
    def test_terminate(self):
        """ Test terminating the monitored process. """
        def slot_finished():
            self.__finished = True
        def childfunc(process):
            while True:
                time.sleep(0.1)
        
        procmon = _process.ThreadedProcessMonitor()
        self.__finished = False
        self._connect_to(procmon.sig_finished, slot_finished)
        procmon(childfunc)
        procmon.terminate_process(wait=True)
        self.assert_(self.__finished)