""" Various utility functionality.
@var Os_Linux: Identifier for the Linux operating system.
@var Os_Windows: Identifier the Windows operating system.
@var Os_Mac: Identifier for the Mac OS operating system.
OsCollection_Posix: Collection of identifiers for POSIX OSes.
"""
import stat, shutil, os.path, imp, fnmatch, sys, errno, \
        codecs
try: import hashlib
except ImportError: import sha
import functools

from srllib.error import *
from srllib._common import *

class PermissionsError(SrlError):
    """ Filesystem permissions error.
    @ivar reason: Original reason for error.
    """
    def __init__(self, path, reason=None):
        SrlError.__init__(self, "Unsufficient permissions for %s" % (path,))
        self.reason = reason

def no_op(*args, **kwds):
    """ Utility no-op function that accepts any arguments/keywords. """
    pass

Checksum_Hex, Checksum_Binary = 0, 1

def get_checksum(path, format=Checksum_Hex, callback=no_op):
    """ Obtain the sha1 checksum of a file or directory.

    If path points to a directory, a collective checksum is calculated
    recursively for all files in the directory tree.
    @param path: Path to file or directory
    @param format: One of L{Checksum_Hex}, L{Checksum_Binary}.
    @param callback: Optionally supply a callback to be periodically called. Raise
    Canceled from this to cancel the operation.
    @return: If hexadecimal, a 40 byte hexadecimal digest. If binary, a 20byte
    binary digest.
    @raise ValueError: Invalid format.
    @raise Canceled: The callback indicated that the operation should be
    canceled.
    """
    if format not in (Checksum_Hex, Checksum_Binary):
        raise ValueError("Invalid format")

    def performSha1(path, shaObj):
        f = file(path)
        try:
            while True:
                callback()
                bytes = f.read(8192)
                shaObj.update(bytes)
                if len(bytes) < 8192:
                    break
        finally:
            f.close()

    try: shaObj = hashlib.sha1()
    except NameError: shaObj = sha.new()
    if format == Checksum_Hex:
        shaMthd = shaObj.hexdigest
    else:
        shaMthd = shaObj.digest

    if os.path.isdir(path):
        for dpath, dnames, fnames in walkdir(path):
            for fname in fnames:
                performSha1(os.path.join(dpath, fname), shaObj)
    else:
        performSha1(path, shaObj)

    return shaMthd()

def get_module(name, path):
    """ Search for a module along a given path and load it.
    @param name: Module name.
    @param path: Path of directories to search. A single-directory path can be
    expressed as a string.
    @raise ValueError: Module not found.
    """
    if isinstance(path, basestring):
        path = [path]
    try:
        file_, fname, extra = imp.find_module(name, path)
        mod = imp.load_module(name, file_, fname, extra)
    except ImportError:
        raise ValueError(name)
    return mod


#{ Filesystem utilities

def replace_root(path, new_root, orig_root=None):
    """ Replace one root directory component of a pathname with another.
    @param path: The pathname.
    @param new_root: The root to replace the old root component with.
    @param orig_root: The original root component to replace, if C{None} the
    first directory component.
    @return: The new pathname.
    @raise ValueError: Original root not found in pathname.
    """
    # Make sure to normalize path, e.g. to convert UNIX-style separators on
    # Windows
    path = os.path.normpath(path)
    # If the new root is empty, leave it be
    if new_root:
        new_root = os.path.normpath(new_root)
    if os.path.sep not in path:
        # No directory component
        return path

    if orig_root is None:
        # Find first dir component
        orig_root = ""
        assert path
        for c in path:
            if c != os.path.sep:
                orig_root += c
            else:
                break
    else:
        orig_root = os.path.normpath(orig_root)
    if not orig_root or orig_root[-1] != os.path.sep:
        orig_root += os.path.sep
    if not path.startswith(orig_root):
        raise ValueError("Path '%s' doesn't start with specified original root '%s'" %
                (path, orig_root))

    relPath = path[len(orig_root):]
    return os.path.join(new_root, relPath)

def _raise_permissions(func):
    """ Decorator for raising PermissionsError upon filesystem access error. """
    @functools.wraps(func)
    def wrapper(*args, **kwds):
        try: return func(*args, **kwds)
        except EnvironmentError, err:
            if err.errno == errno.EACCES:
                import stat
                mode = stat.S_IMODE((os.lstat(os.path.dirname(err.filename)).st_mode)) & stat.S_IEXEC
                raise PermissionsError(err.filename)
            else:
                raise

    return wrapper

class DirNotEmpty(SrlError):
    pass

@_raise_permissions
def remove_dir(path, ignore_errors=False, force=False, recurse=True):
    """ Remove directory, optionally a whole directory tree (recursively).

    @param ignore_errors: Ignore failed deletions?
    @param force: On Windows, force deletion of read-only files?
    @param recurse: Delete also contents, recursively?
    @raise ValueError: The directory doesn't exist.
    @raise PermissionsError: Missing file-permissions.
    @raise DirNotEmpty: Directory was not empty, and recurse was not specified.
    """
    logger.debug("Removing directory '%s' (ignore_errors: %s, force: %s, "
        "recurse: %s)" % (path, ignore_errors, force, recurse))

    def rmdir(path):
        if force:
            # When in force mode, make the directory writeable if necessary
            mode = get_file_permissions(path)
            if not mode & stat.S_IWRITE:
                logger.debug("Adding write permission to directory '%s'" %
                        (path,))
                mode |= stat.S_IWRITE
                chmod(path, mode)

        assert not os.listdir(path), "Directory not empty: '%s'" % (path,)
        logger.debug("Removing directory '%s' itself" % (path,))
        try: os.rmdir(path)
        except OSError:
            logger.debug("Failed to remove directory '%s'" % (path,))
            if not ignore_errors:
                raise

    def handle_err(dpath):
        """Hook for handling errors in walkdir."""
        if not force:
            raise PermissionsError(dpath)
        logger.debug("Making directory '%s' traversable by adding exec and read permissions" %
                (dpath,))
        os.chmod(dpath, stat.S_IEXEC | stat.S_IREAD)
        return True

    if not os.path.exists(path):
        raise ValueError("Directory doesn't exist: %s" % path)

    if recurse:
        for dpath, dnames, fnames in walkdir(path, topdown=False, errorfunc=
                handle_err):
            logger.debug("In directory '%s', subdirectories: %r, child files: %r" %
                    (dpath, dnames, fnames))

            if force:
                # Make the directory writeable if necessary -- on Unix you
                # can't delete children of read-only directories
                mode = get_file_permissions(dpath)
                if not mode & stat.S_IWRITE:
                    logger.debug("Making directory '%s' writeable" % (dpath,))
                    mode |= stat.S_IWRITE
                    chmod(dpath, mode)
            
            for d in dnames:
                abspath = os.path.join(dpath, d)
                if not os.path.islink(abspath):
                    rmdir(abspath)
                else:
                    # Better to remove symlinks as files, since it doesn't
                    # matter if they're broken
                    logger.debug("'%s' is a link" % (d,))
                    remove_file(abspath, force=force)
            for f in fnames:
                remove_file(os.path.join(dpath, f), force=force)
    else:
        if os.listdir(path):
            raise DirNotEmpty
    rmdir(path)

@_raise_permissions
def get_file_permissions(path):
    """ Get permissions flags (bitwise) for a file/directory.

    Links are not dereferenced.
    """
    return stat.S_IMODE(os.lstat(path).st_mode)

@_raise_permissions
def move_file(src, dest, force=False):
    """ Move a file, cross-platform safe.

    This a simple convenience wrapper, for handling snags that may arise on
    different platforms.
    @param force: On Windows, overwrite write-protected destination?
    """
    if get_os_name() == Os_Windows and os.path.isfile(dest):    #pragma: optional
        # Necessary on Windows
        if force:
            dstMode = get_file_permissions(dest)
            if not dstMode & stat.S_IWRITE:
                chmod(dest, dstMode | stat.S_IWRITE)
        os.remove(dest)
    shutil.move(src, dest)

def clean_path(path):
    """ Return a clean, absolute path. """
    return os.path.abspath(os.path.normpath(path))

def _walkdir_handle_err(path):
    raise PermissionsError(path)

@_raise_permissions
def walkdir(path, errorfunc=None, topdown=True, ignore=None):
    """ Directory tree generator.

    This function works in much the same way as os.walk, but expands somewhat
    on that.
    @param path: Directory to traverse.
    @param errorfunc: Function to handle error when a directory can't be
    traversed. Return False from this to ignore directory.
    @param topdown: Traverse in topdown fashion?
    @param ignore: Optionally provide a set of filenames to ignore.
    @raise PermissionsError: Missing permission to traverse directory.
    """
    if errorfunc is None:
        errorfunc = _walkdir_handle_err

    mode = get_file_permissions(path)
    if not mode & stat.S_IREAD:
        if not errorfunc(path):
            # Ignore directory
            return

    if ignore is None:
        ignore = []

    dnames, fnames = [], []
    for e in os.listdir(path):
        if e in ignore:
            continue

        if os.path.isdir(os.path.join(path, e)):
            dnames.append(e)
        else:
            fnames.append(e)

    if topdown:
        yield path, dnames, fnames
    for d in dnames:
        if os.path.islink(os.path.join(path, d)):
            continue
        for x in walkdir(os.path.join(path, d), errorfunc=errorfunc,
                topdown=topdown):
            yield x
    if not topdown:
        yield path, dnames, fnames

@_raise_permissions
def _copy_file(srcpath, dstpath, callback, fs_mode=None):
    if not os.path.exists(srcpath):
        raise MissingSource(srcpath)

    st = os.stat(srcpath)
    sz = float(st.st_size)
    if sz == 0:
        # Just create the destination file
        file(dstpath, "wb").close()
        callback(100)
    else:
        src = file(srcpath, "rb")
        dst = file(dstpath, "wb")
        try:
            while True:
                bytes = src.read(8192)
                dst.write(bytes)
                bytesRead = len(bytes)
                callback(bytesRead / sz * 100)
                if bytesRead < 8192:
                    break
        finally:
            src.close()
            dst.close()

    if fs_mode is None:
        shutil.copystat(srcpath, dstpath)
    else:
        chmod(dstpath, fs_mode)

def copy_file(sourcepath, destpath, callback=no_op, fs_mode=None):
    """ Copy a file.
    @param sourcepath: Source file path.
    @param destpath: Destination file path.
    @param callback: Optional callback to be invoked periodically with progress
    status.
    @param fs_mode: Optionally, specify mode to create destination file with.
    @raise MissingSource: Source file is missing.
    raise PermissionsError: Missing filesystem permissions.
    """
    _copy_file(sourcepath, destpath, callback, fs_mode=fs_mode)

@_raise_permissions
def remove_file(path, force=False):
    """ Remove a file.
    @param force: Force deletion of read-only file?
    @raise PermissionsError: Missing file-permissions.
    """
    logger.debug("Removing file '%s'" % (path,))
    if force:
        # Make the necessary file/directory writeable if it isn't already
        old_mode = get_file_permissions(path)
        if not old_mode & stat.S_IWRITE:
            logger.debug("Adding write permission so file can be removed")
            chmod(path, old_mode | stat.S_IWRITE)

    os.remove(path)

def remove_file_or_dir(path, force=False, recurse=True):
    """ Remove a filesystem object, whether it is a file or a directory.
    @param force: On Windows, force deletion of read-only files?
    @param recurse: Delete recursively, if a directory?
    @raise PermissionsError: Missing file-permissions.
    @raise DirNotEmpty: Directory was not empty, and recurse was not specified.
    """
    if os.path.isdir(path):
        remove_dir(path, force=force, recurse=recurse)
    else:
        remove_file(path, force=force)

class DestinationExists(SrlError):
    pass

class MissingSource(SrlError):
    pass

CopyDir_New, CopyDir_Delete, CopyDir_Merge = range(3)

class _CopyDirCallback:
    """ Translate from per-file progress to directory progress. """
    def __init__(self, total, callback):
        self.__total, self.__callback = (float(total), callback)
        self.__progress = 0.0

    def __call__(self, progress):
        self.__callback(self.__progress + progress*self.__cur_mult)

    def start_file(self, size):
        if self.__total != 0:
            self.__cur_mult = size / self.__total
        else:
            self.__cur_mult = 0

    def end_file(self):
        self.__progress += 100 * self.__cur_mult

@_raise_permissions
def copy_dir(sourcedir, destdir, callback=no_op, ignore=[], mode=CopyDir_New,
        copyfile=None, fs_mode=None):
    """ Copy a directory and its contents.

    Custom File Copying
    ===================
    It is possible to specialize file copying by passing a function for the
    I{copyfile} parameter. This function receives for its two first arguments
    pathnames for the source and destination file respectively, and then a
    callback function. This function is not called with directories or symlinks.

    The callback should be called periodically during copying, with progress
    percentage as a float.
    @param sourcedir: Source directory.
    @param destdir: Destination directory.
    @param callback: Optional callback to be invoked periodically with progress
    status. Raise L{Canceled} from this to cancel.
    @param ignore: Optional list of filename glob patterns to ignore.
    @param mode: Specify the copying mode. CopyDir_New means to refuse copying
    onto an existing directory, CopyDir_Delete means delete existing
    destination, CopyDir_Merge means copying contents of source directory into
    destination directory.
    @param copyfile: Optionally supply a custom function for copying individual
    files.
    @param fs_mode: The numeric mode to create files/directories with.
    @raise MissingSource: The source directory doesn't exist.
    @raise DirectoryExists: The destination directory already exists (and
    mode is CopyDir_New).
    @raise PermissionsError: Missing permission to perform operation.
    @raise Canceled: The callback requested canceling.
    """
    if os.path.exists(destdir):
        if mode == CopyDir_New:
            raise DestinationExists(destdir)
        elif mode == CopyDir_Delete:
            remove_file_or_dir(destdir)

    def filter(names):
        """ Filter list of filesystem names in-place. When using os.walk,
        directories removed from the list won't be traversed. """
        for ptrn in ignore:
            for name in names[:]:
                if fnmatch.fnmatch(name, ptrn):
                    names.remove(name)
        return names

    def update_mode(src, dst):
        """Potentially copy mode from source to destination."""
        if get_os_name() == Os_Windows:
            # Won't work on Windows
            return

        if fs_mode is None:
            # Only copy if mode isn't already specified
            shutil.copystat(src, dst)

    if not os.path.exists(sourcedir):
        raise MissingSource(sourcedir)

    mkdir_kwds = {}

    if not os.path.exists(destdir):
        if fs_mode is not None:
            mkdir_kwds["mode"] = fs_mode
        os.makedirs(destdir, **mkdir_kwds)
    update_mode(sourcedir, destdir)

    # We figure out the total number of bytes, for computing progress
    allbytes = 0
    for dpath, dnames, fnames in walkdir(sourcedir):
        for d in filter(dnames):
            allbytes += 1
        for f in filter(fnames):
            allbytes += os.lstat(os.path.join(dpath, f)).st_size

    if copyfile is None:
        copyfile = _copy_file
    mycallback = _CopyDirCallback(allbytes, callback)

    # First invoke the callback with a progress of 0
    callback(0)
    for dpath, dnames, fnames in walkdir(sourcedir):
        for d in filter(dnames):
            srcpath = os.path.join(dpath, d)
            dstpath = replace_root(srcpath, destdir, sourcedir)
            if os.path.exists(dstpath):
                remove_file_or_dir(dstpath)
            os.mkdir(dstpath, **mkdir_kwds)
            update_mode(srcpath, dstpath)
            mycallback.start_file(1)
            mycallback(100)
            mycallback.end_file()
        for f in filter(fnames):
            srcpath = os.path.join(dpath, f)
            dstpath = replace_root(srcpath, destdir, sourcedir)
            if os.path.exists(dstpath):
                remove_file_or_dir(dstpath)
            if hasattr(os, "symlink") and os.path.islink(srcpath):
                linktgt = os.readlink(srcpath)
                os.symlink(linktgt, dstpath)
                continue

            mycallback.start_file(os.lstat(srcpath).st_size)
            copyfile(srcpath, dstpath, mycallback, fs_mode=fs_mode)
            mycallback.end_file()

def create_tempfile(suffix="", prefix="tmp", close=True, content=None,
        encoding=None, dir=None):
    """ Create temporary file.

    The file is opened in R/W mode.
    @param suffix: Optional filename suffix.
    @param prefix: Optional filename prefix.
    @param close: Close the file after creating it?
    @param content: Optional content to write to file.
    @param encoding: Specify text encoding for file.
    @param dir: Optionally specify directory for the file.
    @return: If C{close} path to created temporary file, else temporary file.
    """
    import tempfile
    (fd, fname) = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
    # File should not be automatically deleted
    os.close(fd)

    if not close or content:
        # Open file directly instead of using fdopen, since the latter will
        # return a file with a bogus name
        try:
            if encoding is None:
                f = file(fname, "w+")
            else:
                f = codecs.open(fname, "w+", encoding)
            try:
                if content:
                    f.write(content)
                    # Make sure to reset the file position!
                    f.seek(0)
            except:
                f.close()
                raise
            if close:
                f.close()
                return fname
        except:
            # Make sure to delete created file
            os.remove(fname)
            raise
        return f
    return fname

def create_file(name, content="", binary=False, encoding=None, close=True):
    """ Create a file, with optional content.
    @param name: Filename.
    @param content: Optional content to write to file.
    @param binary: Create file in binary mode (makes a difference on Windows)?
    @param encoding: Specify text encoding of file content.
    @param close: Close file? If true, the file is returned, else its name is
    returned.
    @return: Path to created file.
    """
    mode = "w"
    if binary:
        mode += "b"
    if encoding is None:
        f = file(name, mode)
    else:
        f = codecs.open(name, mode, encoding)
    try:
        if content:
            f.write(content)
    except:
        f.close()
        raise
    if close:
        f.close()
        return name
    return f

def read_file(name, binary=False, encoding=None):
    """ Read content of file.
    @param name: Filename.
    @param binary: Open in binary mode (makes a difference on Windows)?
    @param encoding: Optionally specify text encoding of file content.
    @return: File content as string.
    """
    if not binary:
        mode = "rb"
    else:
        mode = "r"
    if encoding is None:
        f = file(name, mode)
    else:
        f = codecs.open(name, mode=mode, encoding=encoding)
    try: content = f.read()
    finally: f.close()

    return content

def _sig(st):
    return (stat.S_IFMT(st.st_mode), st.st_size, stat.S_IMODE(st.st_mode),
            st.st_uid, st.st_gid)

def compare_dirs(dir0, dir1, shallow=True, ignore=[], filecheck_func=None):
    """ Check that the contents of two directories match.

    Contents that mismatch and content that can't be found in one directory or
    can't be checked somehow are returned separately.
    @param shallow: Just check the stat signature instead of reading content
    @param ignore: Names of files(/directories) to ignore
    @param filecheck_func: Optionally provide function for deciding whether
    two files are alike.
    @raise ValueError: One of the directories are missing.
    @return: Pair of mismatched and failed pathnames, respectively
    """
    def checkfiles(path0, path1):
        chksum0, chksum1 = (get_checksum(path0, format=Checksum_Binary),
            get_checksum(path1, format=Checksum_Binary))
        r = chksum0 == chksum1
        if not r:
            sys.stderr.write("%s mismatched against %s because %s != %s\n" %
                    (path0, path1, chksum0, chksum1))
        return r

    if filecheck_func is None:
        filecheck_func = checkfiles
    mismatch = []
    error = []
    if not os.path.exists(dir0):
        raise ValueError("First directory missing: '%s'" % (dir0,))
    if not os.path.exists(dir1):
        raise ValueError("Second directory missing: '%s'" % (dir1,))
    if len(os.listdir(dir0)) == 0:
        # Indicate any files in dir1 as erroneus
        return mismatch, os.listdir(dir1)

    if dir0[-1] != os.path.sep:
        dir0 = dir0 + os.path.sep

    def handle_err(dpath):
        # Don't traverse this directory
        return False
    for dpath, dnames, fnames in walkdir(dir0, handle_err):

        # Filter out files to ignore
        for ign in ignore:
            while ign in dnames:
                dnames.remove(ign)
            while ign in fnames:
                fnames.remove(ign)

        reldir = dpath[len(dir0):]
        assert reldir != dpath, dpath

        contents0 = dnames + fnames
        contents1 = [e for e in os.listdir(os.path.join(dir1, reldir)) if e not
            in ignore]

        lnth0, lnth1 = len(contents0), len(contents1)
        if lnth0 < lnth1:
            for name in contents1:
                if name not in contents0:
                    error.append(os.path.join(reldir, name))

        for name in contents0:
            relpath = os.path.join(reldir, name)
            try:
                path0, path1 = os.path.join(dir0, relpath), os.path.join(dir1,
                        relpath)
                st0, st1 = os.lstat(path0), os.lstat(path1)
                mismatched = False
                s0, s1 = _sig(st0), _sig(st1)
                if name in fnames:
                    if s0 != s1:
                        sys.stderr.write("%s mismatched because %r != %r\n" %
                                (path1, s0, s1))
                        mismatched = True
                    elif not shallow:
                        mismatched = not filecheck_func(path0, path1)
                else:
                    assert name in dnames
                    mismatched = s0[2:] != s1[2:]   # Ignore format and size
                    if mismatched:
                        # No need to traverse this directory
                        sys.stderr.write("Mismatched: %r, %r\n" % (s0[1:],
                            s1[1:]))
                        dnames.remove(name)
                if mismatched:
                    mismatch.append(relpath)
            except OSError:
                if name in dnames:
                    dnames.remove(name)
                error.append(relpath)

    return mismatch, error

@_raise_permissions
def chmod(path, mode, recursive=False):
    """ Wrapper around os.chmod, which allows for recursive modification of a
    directory tree.
    @param path: Path to modify.
    @param mode: New permissions mode.
    @param recursive: Apply recursively, if directory?
    @raise PermissionsError: Missing file-permissions.
    """
    made_exec = []

    def _chmod(path, fixexec=False):
        newmode = mode
        if fixexec and os.path.isdir(path) and not mode & stat.S_IEXEC:
            # Make the directory accessible
            newmode |= stat.S_IEXEC
            made_exec.append(path)

        os.chmod(path, newmode)

    if recursive and os.path.isdir(path):
        seen = set()
        for dpath, dnames, fnames in walkdir(path):
            assert dpath not in seen, "Already entered %s" % (dpath,)
            seen.add(dpath)
            _chmod(dpath, fixexec=True)

            for d in dnames[:]:
                # Chmod empty dirs now
                os.listdir(os.path.join(dpath, d))
                if not os.listdir(os.path.join(dpath, d)):
                    _chmod(os.path.join(dpath, d))
                    dnames.remove(d)
            for f in fnames:
                _chmod(os.path.join(dpath, f))

        # Now finalize the executable bit in depth-first fashion
        for dpath in reversed(made_exec):
            _chmod(dpath)
    else:
        _chmod(path)

def resolve_path(executable):
    """Resolve name of executable into absolute path.

    On Windows, we will use win32api.FindExecutable if preferable, otherwise
    we will use the standard algorithm. Note on this platform, though, that if
    the executable doesn't have one of the possible extensions
    of an executable, as defined in $PATHEXTS, we will search the path for a
    combination of the filename and any extension in $PATHEXTS (e.g., .exe).
    @raise NotFound: The executable was not found in path.
    @raise ValueError: An invalid filename was passed.
    """
    if os.path.sep in executable:
        raise ValueError("Invalid filename: %s" % executable)
    if get_os_name() == Os_Windows:    # pragma: optional
        try: import win32api, pywintypes
        except ImportError: pass
        else:
            try: exepath = win32api.FindExecutable(executable)[1]
            except pywintypes.error: raise NotFound(executable)
            return exepath

    # Default solution, search path ourselves

    path = os.environ.get("PATH", "").split(os.pathsep)
    if get_os_name() == Os_Windows:
        # PATHEXTS tells us which extensions an executable may have
        path_exts = os.environ.get("PATHEXTS", ".exe;.bat").split(";")
        has_ext = os.path.splitext(executable)[1] in path_exts
        if not has_ext:
            exts = path_exts
        else:
            # Don't try to append any extensions
            exts = [""]
    else:
        # General, executables don't have extensions
        exts = [""]
    for d in path:
        try:
            for ext in exts:
                exepath = os.path.join(d, executable + ext)
                if os.access(exepath, os.X_OK):
                    return exepath
        except OSError:
            pass

    raise NotFound(executable)

#}

class Command(object):
    """ Curry a function with associated parameters.

    The rationale for this class is to be able to store a function and certain
    parameters to supply it with.
    """
    def __init__(self, callback, callback_args=(), callback_kwds={}):
        self.__cb = callback
        self.__cb_args, self.__cb_kwds = callback_args, callback_kwds

    def __call__(self):
        self.__cb(*self.__cb_args, **self.__cb_kwds)
