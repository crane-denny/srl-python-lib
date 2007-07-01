""" Test the signal module. """
import os.path, time, signal

from srllib.testing import *
import srllib.process as _process
from _common import *

class TestError(_process.PickleableException):
    pass

def _childfunc_writes(outstr, errstr):
    for i in range(10):
        sys.stdout.write("%s\n" % outstr)
        sys.stderr.write("%s\n" % errstr)
    
def _childfunc_raises():
        raise TestError("TestError")

def _childfunc_sleeps():
    import time
    while True:
        time.sleep(0.1)

class ProcessTest(TestCase):
    
    def test_child_exception(self):
        """ Test catching an exception raised in the child. """
        proc = _process.Process(_childfunc_raises)
        try: proc.wait()
        except _process.ChildError, err:
            self.assert_(isinstance(err.orig_exception, TestError))
        else:
            print proc.stderr.read()
            raise AssertionError, "Exception not raised"
        # Polling should raise the same error
        self.assertRaises(_process.ChildError, proc.poll)
        proc.close()
        
    def test_terminate(self):
        """ Test terminating the child process. """
        proc = _process.Process(_childfunc_sleeps)
        self.assertEqual(proc.terminate(), -signal.SIGTERM)
        # Make sure that it is safe to call this after the process has exited
        self.assertEqual(proc.terminate(), -signal.SIGTERM)
    
    '''
    def test_run_in_terminal(self):
        """ Test running code in virtual terminal. """
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
            
            procmon(_childfunc_writes, ["Test out", "Test err"])
            procmon.wait()

            for l in self.__stdout.splitlines():
                self.assertEqual(l, "Test out")
            for l in self.__stderr.splitlines():
                self.assertEqual(l, "Test err")
    '''
       
def _childfunc_succeeds():
    pass  

def _childfunc_fails():
    raise Exception("Failure")     
                
class ThreadedProcessMonitorTest(TestCase):
    """ Test the threaded process monitor. """
    '''
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
    '''
    
    def test_success(self):
        """ Verify that sig_finished is received when the process finishes
        successfully. """
        def slot_finished():
            self.__finished = True
        def slot_failed(err):
            self.__failed = True
        
        procmon = _process.ThreadedProcessMonitor()
        self.__finished = self.__failed = False
        self._connect_to(procmon.sig_finished, slot_finished)
        self._connect_to(procmon.sig_failed, slot_failed)
        procmon(_childfunc_succeeds)
        procmon.wait()
        self.assert_(self.__finished)
        self.assertNot(self.__failed)
        
    def test_failure(self):
        """ Verify that sig_failed is received when the process fails. """
        def slot_finished():
            self.__finished = True
        def slot_failed(err):
            self.__error = err
        
        procmon = _process.ThreadedProcessMonitor()
        self.__finished = False
        self.__error = None
        self._connect_to(procmon.sig_finished, slot_finished)
        self._connect_to(procmon.sig_failed, slot_failed)
        procmon(_childfunc_fails)
        procmon.wait()
        self.assert_(isinstance(self.__error, _process.ChildError), self.__error)
        self.assertNot(self.__finished)
    