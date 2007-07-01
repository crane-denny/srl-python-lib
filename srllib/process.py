""" Functionality for managing child processes. """
# Don't import signal from this package
from __future__ import absolute_import
import os.path, struct, cPickle, sys, signal, traceback, subprocess, errno, \
    stat, time

from srllib import threading, util
from srllib._common import *
from srllib.error import BusyError, SrlError
         
class ChildError(SrlError):
    """ Exception detected in child process.
    
    If the original exception derives from L{PickleableException}, it is
    preserved, along with the traceback.
    @ivar orig_exception: The original exception, possibly C{None}.
    @ivar orig_traceback: Traceback of original exception, possibly C{None}.
    """
    def __init__(self, process_error):
        SrlError.__init__(self, "Error in child process")    
        if process_error.exc_class is not None:
            assert process_error.exc_message is not None 
            assert process_error.exc_traceback is not None
            assert process_error.exc_arguments is not None
            self.orig_exception = process_error.exc_class(*process_error.exc_arguments)
        else:
            self.orig_exception = None
        self.orig_traceback = process_error.exc_traceback
                    
class PickleableException(SrlError):
    def __init__(self, msg, *args):
        SrlError.__init__(self, msg)
        self.arguments = (msg,) + args

class _ProcessError(object):
    """ Encapsulation of a child process error.
    
    Exceptions don't pickle in the standard fashion, so we do it like this.
    @ivar message: Error message.
    @ivar exc_message: Original exception message.
    @ivar exc_class: Class of original exception.
    @ivar exc_arguments: Arguments of original exception.
    @ivar exc_traceback: Traceback of original exception.
    """
    def __init__(self, msg, original_exc=None, original_tb=None):
        self.message = msg
        
        sys.stderr.write("ProcessError: %r\n" % (original_exc,))
        sys.stderr.flush()
        if original_exc is not None:            
            self.exc_message = str(original_exc)
        else:
            self.exc_message = None
        if isinstance(original_exc, PickleableException):
            self.exc_class = original_exc.__class__
            self.exc_arguments = original_exc.arguments
        else:
            self.exc_class = None
            self.exc_arguments = None
        if original_tb is not None:
            self.exc_traceback = traceback.format_tb(original_tb)
        else:
            self.exc_traceback = None
            
class PickleError(SrlError):
    pass

class _MthdProxy(object):
    def __init__(self, mthd):
        self.__obj, self.__cls, self.__name = mthd.im_self, mthd.im_class, \
            mthd.im_func.func_name

    def __call__(self, *args, **kwds):
        name = self.__name
        if name.startswith("__"):
            # Mangle
            name = "_%s%s" % (self.__cls.__name__, name)
        func = getattr(self.__cls, name)
        func(self.__obj, *args, **kwds)

class ChildDied(SrlError):
    """ Child died unexpectedly.
    @ivar exitcode: Child's exit code.
    @ivar stderr: Child's stderr.
    """
    def __init__(self, exitcode, stderr):
        SrlError.__init__(self, "Child died unexpectedly (exit code %d)" %
                          exitcode)
        self.exitcode, self.stderrr = exitcode, stderr
            
class Process(object):
    """ Invoke a callable in a child process.

    Instantiating an object of this class will spawn a child process, I{in which a
    provided callable is invoked}. Pipes are provided for the standard streams
    and a separate pipe for communication between parent and child. stdout and
    stderr are made non-blocking so they can easily be drained of data.
    @ivar stdout: Child's stdout file.
    @ivar stderr: Child's stderr file..
    """
    def __init__(self, child_func, child_args=[], child_kwds={}):
        """
        @param child_func: Function to be called in child process.
        @param child_args: Optional arguments for the child function.
        @param child_kwds: Optional keywords for the child function.
        @raise ChildDied: Child died unexpectedly.
        """
        self.__exit_rslt = None
        # We execute in the child a script which first unpickles the function
        # and its parameters, and then invokes it. This is the best cross-
        # platform approach that we've found (since Windows does not support
        # fork)
        script_fname = self.__script_fname = util.create_tempfile(content=
r"""import cPickle, sys, struct
pipe_path = sys.argv[1]
lnth = struct.unpack("@I", sys.stdin.read(4))[0]
sys.path = cPickle.loads(sys.stdin.read(lnth))
lnth = struct.unpack("@I", sys.stdin.read(4))[0]
func, args, kwds = cPickle.loads(sys.stdin.read(lnth))
try: func(*args, **kwds)
except Exception, err:
    from srllib.process import _ProcessError
    pickle = cPickle.dumps(_ProcessError("Error in child", err, sys.exc_info()[2]))
    f = file(pipe_path, "wb")
    try: f.write(pickle)
    finally: f.close()
""")
        
        # XXX: Some day we might want to use a real (named) pipe ...
        pipe_path = self.__errpipe_path = util.create_tempfile()
        prcs = self.__prcs = subprocess.Popen(["python", script_fname, pipe_path],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, universal_newlines=
                                    True, bufsize=-1)
        
        import types
        if isinstance(child_func, types.MethodType):
            # Can't pickle instance methods
            child_func = _MthdProxy(child_func)
        # Pickle the path, to ensure proper unpickling
        path_data = cPickle.dumps(sys.path)
        try: func_data = cPickle.dumps((child_func, child_args, child_kwds))
        except TypeError, err:
            print err
            raise PickleError("Failed to pickle %r, is this e.g. a nested definition?" % \
                    child_func)
        try:
            prcs.stdin.write(struct.pack("@I", len(path_data)))
            prcs.stdin.write(path_data)
            prcs.stdin.write(struct.pack("@I", len(func_data)))
            prcs.stdin.write(func_data)
            # Important: Flush what we've written so child isn't stuck waiting for data
            prcs.stdin.flush()
        except EnvironmentError, err:
            if err.errno == errno.EPIPE:
                exitcode = self.wait()
                raise ChildDied(exitcode, prcs.stderr.read())
            raise

        self._pid = prcs.pid
        if get_os_name() == Os_Windows:
            import win32api
            # Open with rights to terminate and synchronize
            self.__prcs_handle = win32api.OpenProcess(0x1 | 0x100000, False,
                                    self.pid)

    def __str__(self):
        return self.name

    @property
    def pid(self):
        return self._pid
    
    @property
    def stdout(self):
        return self.__prcs.stdout
    
    @property
    def stderr(self):
        return self.__prcs.stderr

    def close(self):
        """ Release resources.

        If the process is still alive, it is waited for.
        """
        os.remove(self.__errpipe_path)
        if self.__exit_rslt is None:
            self.wait()
            
    def poll(self):
        """ Check if child has exited.
        @return: If child has exited, its exit code, else C{None}.
        """
        rslt = self.__exit_rslt
        if rslt is not None:
            if isinstance(rslt, ChildError):
                raise rslt 
            assert isinstance(rslt, int)
            return rslt
        r = self.__prcs.poll()
        f = file(self.__errpipe_path, "rb")
        try: data = f.read()
        finally: f.close()
        if data:
            # Exception from child process
            err = cPickle.loads(data)
            self.__exit_rslt = ChildError(err)            
            raise self.__exit_rslt
        return r

    def wait(self):
        """ Wait for child to finish.
        @return: Child's exit code.
        @raise ChildError: Exception detected in child.
        """
        self.__prcs.wait()
        return self.poll()

    def terminate(self):
        """ Kill child process.
        
        This method will block until it is determined that the child has in fact
        terminated.
        @return: The child's exit status.
        """
        r = self.poll()
        if r is not None:
            return r
        if get_os_name() == Os_Windows:
            import win32process
            win32process.TerminateProcess(self.__prcs_handle, 0)
        else:
            try:
                os.kill(self.pid, signal.SIGTERM)
                time.sleep(.05)
            except OSError, err:
                if err.errno == errno.ECHILD:
                    # Presumably, the child is dead already?
                    pass
                else:
                    raise
            if self.poll() is None:
                os.kill(self.pid, signal.SIGKILL)

        return self.wait()

    def write_message(self, message, wait=True):
        """ Write message to other process.
        
        If this is the child process, message will be available for parent process and vice versa.
        This method may wait for the other process to "pick up the phone". A broken connection will
        result in EofError.
        @param message: An arbitrary object.
        @param wait: Wait for acknowledgement.
        """
        msg = cPickle.dumps(message)
        self.pipe_out.write(struct.pack("i", len(msg)))
        self.pipe_out.write(msg)
        if not wait:
            return
        # Wait for ack
        a = self.pipe_in.read(1)
        if a == "":
            raise EofError

    def read_message(self):
        """ Read message from other process.
        
        If this is the child process, message will be read from parent process
        and vice versa. This method will wait until a message is actually
        received.
        @return: An arbitrary object written by the other process
        @raise EofError: Broken connection.
        """
        def read_data(lnth):
            data = self.pipe_in.read(lnth)
            if len(data) < lnth:
                raise EofError
            return data
        
        data = read_data(struct.calcsize("i"))
        msgLnth = struct.unpack("i", data)[0]
        data = read_data(msgLnth)

        # Ack
        try: self.pipe_out.write('a')
        except IOError: pass

        import cPickle
        obj = cPickle.loads(data)
        return obj

    def _poll(self, wait=False):
        if self._childRet is not None:
            return self._childRet

        if wait:
            flag = 0
        else:
            flag = os.WNOHANG
        while True:
            try: pid, status = os.waitpid(self._pid, flag)
            except OSError, err:
                # Ignore interrupts
                if err.errno == errno.EINTR:
                    continue
                raise
            break

        if pid != self._pid:
            return None

        if os.WIFSIGNALED(status):
            self._childRet = -os.WTERMSIG(status)
        else:
            self._childRet = os.WEXITSTATUS(status)

        if self._childRet != 0:
            try: obj = self.read_message()
            except EofError:
                pass
            else:
                if isinstance(obj, _ProcessError):
                    raise ChildError(obj)
        return self._childRet


class EofError(IOError):
    pass

class ThreadedProcessMonitor(object):
    """ Monitor a child process in a background thread.
    @group Signals: sig*
    @ivar process: The L{child process<Process>}
    @ivar sig_stdout: Triggered to deliver stdout output from the child process.
    @ivar sig_stderr: Triggered to deliver stderr output from the child process-
    @ivar sig_finished: Signal that monitor has finished, from background thread.
    Parameters: None.
    @ivar sig_failed: Signal that monitored process failed, from background thread.
    Paramaters: The caught exception.
    """
    def __init__(self, daemon=False, use_pty=False, pass_process=True):
        """
        @param daemon: Start background threads in daemon mode
        @param use_pty: Open pseudo-terminal for child process.
        @param pass_process: When executing functions in child processes,
        should the L{Process} object be passed as a parameter?
        """
        self.sig_stdout, self.sig_stderr, self.sig_finished, self.sig_failed = \
                Signal(), Signal(), Signal(), Signal()
        self.__process = None
        i, o = os.pipe()
        self._event_pipe_in, self._event_pipe_out = os.fdopen(i, "r", 0), os.fdopen(o, "w", 0)
        self._daemon = daemon
        self._thrd = None

    def __call__(self, child_func, child_args=[], child_kwds={}):
        """ Execute function in child process, monitored in background thread.
        @param child_func: Function to execute
        @param child_args: Arguments for child function
        @param child_kwds: Keywords for child function
        @raise BusyError: Already busy with a child process.
        """
        if self.__process is not None:
            raise BusyError("Another process is already being monitored")
        self.__exit_code = None
        self.__process = Process(child_func, child_args=child_args, child_kwds=child_kwds)
        thrd = self._thrd = threading.Thread(target=self._thrdfunc, daemon=self._daemon)
        thrd.start()
        
    def monitor_command(self, arguments, cwd=None, env=None):
        if self.__process is not None:
            raise BusyError("Another process is already being monitored")
        self.__process = Process(self.__run_command, child_args=[arguments, cwd, env])
        thrd = self._thrd = threading.Thread(target=self._thrdfunc, daemon=self._daemon)
        thrd.start()
        
    def __run_command(self, process, arguments, cwd, env):
        if cwd is not None:
            os.chdir(cwd)
        os.execve(arguments[0], arguments, env)

    def terminate_process(self, wait=False):
        """ Terminate child process
        @param wait: Wait for process to die? Default False
        """
        self._event_pipe_out.write("t")
        if wait:
            self.wait()

    def wait(self):
        """ Wait for monitoring thread to finish.
        @return: The child process exit code. If the child raised a L{ChildError},
        this will be None.
        """
        if self._thrd is not None:
            self._thrd.join()

        return self.__exit_code

    def _thrdfunc(self):
        import select
        process = self.__process
        stdout, stderr = process.stdout, process.stderr
        pollIn, pollOut, pollEx = [stdout, stderr, self._event_pipe_in], [], []
        while pollIn:
            # Keep in mind that closed files will be seen as ready by select and cause it to wake up
            rd, wr, ex = select.select(pollIn, pollOut, pollEx, 0.01)

            if stdout in rd:
                try: o = stdout.read()
                except IOError:
                    # Presumably EOF
                    o = ""
                if o:
                    self.sig_stdout(o)
                else:
                    pollIn.remove(stdout)
            if stderr in rd:
                e = stderr.read()
                if e:
                    self.sig_stderr(e)
                else:
                    pollIn.remove(stderr)

            if self._event_pipe_in in rd:
                event = self._event_pipe_in.read(1)
                assert event in ("t",)
                if event == "t":
                    # Terminate
                    process.terminate()
                    break
            
            if stdout not in pollIn and stderr not in pollIn:
                # Child exited
                break

        try: self.__exit_code = self.__process.wait()
        except ChildError, err:
            self.sig_failed(err)
        else:
            self.sig_finished()
        self.__process = None
