""" Functionality for managing child processes. """
# Don't import signal from this package
from __future__ import absolute_import
import os.path, struct, cPickle, sys, signal, traceback

from srllib import threading
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
            
class Process(object):
    """ Invoke a callable in a child process.

    Instantiating an object of this class will spawn a child process, I{in which a
    provided callable is invoked}. Pipes are provided for the standard streams
    and a separate pipe for communication between parent and child. stdout and
    stderr are made non-blocking so they can easily be drained of data.
    @ivar stdout: Child's stdout file.
    @ivar stderr: Child's stderr file.
    @ivar pipe_in: File for passing message to other process.
    @ivar pipe_out: File for reading message from other process.
    """
    def __init__(self, child_func, child_args=[], child_kwds={}, name=None,
                 use_pty=False, pass_process=True):
        """
        @param child_func: Function to be called in child process.
        @param child_args: Optional arguments for the child function.
        @param child_kwds: Optional keywords for the child function.
        @param name: Optional name for the process:
        @param use_pty: Open pseudo-terminal for child process.
        @param pass_process: Pass this object as first parameter to child function?
        """
        if name is None:
            name = os.getpid()
        self.name = name
        self.__use_pty, self.__passProcess = use_pty, pass_process
        
        parentRead, parentWrite, childRead, childWrite, readStdout, writeStdout, readStderr, writeStderr = \
                self.__createPipes()
        self.__exec_child(child_func, child_args, child_kwds)
        if self.name is None:
            self.name = "Process<%d>" % (self.pid,)
        self.pipe_in, self.pipe_out = os.fdopen(parentRead, "r", 0), os.fdopen(parentWrite, "w", 0)
        # Open in line-buffered mode
        if self.__use_pty:
            os.close(readStdout)
            readStdout = self.__ptyFd
        self.stdout, self.stderr = os.fdopen(readStdout, "r", 1), os.fdopen(readStderr, "r", 1)

        self._files = self.pipe_in, self.pipe_out, self.stdout, self.stderr

    def __str__(self):
        return self.name

    @property
    def pid(self):
        return self._pid

    def close(self):
        """ Release resources.

        If the process is still alive, it is waited for.
        """
        if self.poll() is None:
            self.wait()
        for f in self._files:
            f.close()

    def poll(self):
        return self._poll(wait=False)

    def wait(self):
        """ Wait for child to die.
        @return: Child's exit code
        @raise ChildError: Exception detected in child.
        """
        return self._poll(wait=True)

    def terminate(self):
        """ Kill child process. This method will block until it is determined that the child has in fact terminated.
        @return: The child's exit status
        """
        import signal, time
        try:
            os.kill(self.pid, signal.SIGTERM)
            time.sleep(.5)
        except OSError:
            # Presumably, the child is dead already?
            pass
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

    if get_os_name() == Os_Windows:   #pragma optional
        def __createPipes(self):
            def createPipe(sattr, convertRead=False, convertWrite=False):
                read, write = win32pipe.CreatePipe(sattr, 0)
                if convertRead:
                    read = msvcrt.open_osfhandle(read.Detach(), 0)
                if convertWrite:
                    write = msvcrt.open_osfhandle(write.Detach(), 0)
                return read, write

            import win32pipe, win32security, msvcrt
            sattr = win32security.SECURITY_ATTRIBUTES()
            sattr.bInheritHandle = 1
            sattr.SECURITY_DESCRIPTOR = None
            self.__childRead, self.__parentWrite = createPipe(sattr, convertWrite=True)
            self.__parentRead, self.__childWrite = createPipe(sattr, True, True)
            self.__readStdout, self.__writeStdout = createPipe(sattr, convertRead=True)
            self.__readStderr, self.__writeStderr = createPipe(sattr, convertRead=True)

            return self.__parentRead, self.__parentWrite, self.__childRead, self.__childWrite, \
                    self.__readStdout, self.__writeStdout, self.__readStderr, self.__writeStderr
    else:
        def __makeNonBlocking(self, fd):
            import fcntl
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            flags |= os.O_NONBLOCK
            fcntl.fcntl(fd, fcntl.F_SETFL, flags)

        def __createPipes(self):
            # Communication between parent-child
            self.__parentRead, self.__childWrite = os.pipe()
            self.__childRead, self.__parentWrite = os.pipe()
            self.__readStdout, self.__writeStdout = os.pipe()
            self.__readStderr, self.__writeStderr = os.pipe()
            self.__makeNonBlocking(self.__readStdout)
            self.__makeNonBlocking(self.__readStderr)

            return self.__parentRead, self.__parentWrite, self.__childRead, self.__childWrite, \
                    self.__readStdout, self.__writeStdout, self.__readStderr, self.__writeStderr

    if get_os_name() == Os_Windows:   #pragma: optional
        def __exec_child(self, child_func, child_args, child_kwds):
            import win32process, win32event, win32api
            sinfo = win32process.STARTUPINFO()
            sinfo.dwFlags |= win32process.STARTF_USESTDHANDLES
            sinfo.hStdInput = childRead
            sinfo.hStdOutput = writeStdout
            sinfo.hStdError = writeStderr

            fname = util.createTemporaryFile()
            try:
                self.__handle, ht, self._pid, tid = win32process.CreateProcess(util.resolvePath("python"), \
                        "python %s" % fname, None, None, 1, 0, None, None, sinfo)
                ht.Close()
                childRead.Close()
                os.close(childWrite)
                writeStdout.Close()
                writeStderr.Close()
            finally:
                os.remove(fname)
    else:
        def __exec_child(self, child_func, child_args, child_kwds):
            self._childRet = None

            if not self.__use_pty:
                pid = os.fork()
            else:
                import pty
                pid, self.__ptyFd = pty.fork()

            self._pid = pid
            if pid == 0:
                # Child
                try:
                    # Make sure that these two point to the expected streams,
                    # since they may have been replaced beforehand
                    sys.stdout = os.fdopen(1, "w")
                    sys.stderr = os.fdopen(2, "w")
                    
                    os.close(self.__parentRead)
                    os.close(self.__parentWrite)
                    os.close(self.__readStdout)
                    os.close(self.__readStderr)

                    if not self.__use_pty:
                        os.dup2(self.__writeStdout, sys.stdout.fileno())
                    os.dup2(self.__writeStderr, sys.stderr.fileno())
                    os.close(self.__writeStdout)
                    os.close(self.__writeStderr)

                    self.pipe_in = os.fdopen(self.__childRead, "r", 0)
                    self.pipe_out = os.fdopen(self.__childWrite, "w", 0)
                    self._files = self.pipe_in, self.pipe_out

                    if self.__passProcess:
                        args = [self] + child_args
                    else:
                        args = child_args
                    child_func(*args, **child_kwds)
                    sys.stdout.flush()
                    sys.stderr.flush()
                except Exception, err:
                    self.write_message(_ProcessError("Exception occurred in child process",
                                                     err, sys.exc_info()[2]), wait=False)
                    os._exit(1)

                os._exit(0)
            else:
                # Parent
                os.close(self.__childRead)
                os.close(self.__childWrite)
                os.close(self.__writeStdout)
                os.close(self.__writeStderr)
                if self.__use_pty:
                    self.__makeNonBlocking(self.__ptyFd)

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
        self.__use_pty, self.__pass_process = use_pty, pass_process

    def __call__(self, child_func, child_args=[], child_kwds={}):
        """ Execute function in child process, monitored in background thread.
        @param child_func: Function to execute
        @param child_args: Arguments for child function
        @param child_kwds: Keywords for child function
        @raise BusyError: Already busy with a child process.
        """
        if self.__process is not None:
            raise BusyError("Another process is already being monitored")
        self.__process = Process(child_func, child_args=child_args, child_kwds=child_kwds, use_pty=\
                self.__use_pty, pass_process=self.__pass_process)
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
        @return: The child process exit code.
        """
        if self._thrd is not None:
            self._thrd.join()

        return self.__exit_code

    def _thrdfunc(self):
        import select
        process = self.__process
        stdout, stderr, childOut = process.stdout, process.stderr, process.pipe_in
        pollIn, pollOut, pollEx = [stdout, stderr, childOut, self._event_pipe_in], [], []
        procErr = None
        while pollIn:
            # Keep in mind that closed files will be seen as ready by select and cause it to wake up
            rd, wr, ex = select.select(pollIn, pollOut, pollEx)

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

            # Read child messages once we have drained the standard streams
            if childOut in rd and not stdout in rd and not stderr in rd:
                # Process message from child
                try:
                    obj = process.read_message()
                except EofError:
                    pollIn.remove(childOut)
                    pollIn = [] # Child is dead, no need to keep polling
                else:
                    if isinstance(obj, _ProcessError):
                        procErr = obj
                        break
                    else:
                        assert not isinstance(obj, Exception)

            if self._event_pipe_in in rd:
                event = self._event_pipe_in.read(1)
                assert event in ("t",)
                if event == "t":
                    # Terminate
                    process.terminate()
                    break

        self.__exit_code = self.__process.wait()
        self.__process = None
        if procErr is None:
            self.sig_finished()
        else:
            self.sig_failed(ChildError(procErr))