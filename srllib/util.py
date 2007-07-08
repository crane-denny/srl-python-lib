""" Various utility functionality.
@var Os_Linux: Tuple of identifiers for known versions of the Linux operating
system
@var Os_Windows: Tuple of identifiers for known versions of the Windows
operating system
"""
import stat, shutil, os.path, imp, platform, fnmatch, sys, errno, \
        codecs
try: import hashlib
except ImportError: import sha
from error import *

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

def _make_decorator(func):
    """ Wrap a test decorator to replicate metadata of the decorated function.
    """
    def decorate(decorated):
        decorated.name = func.__name__
        decorated.__dict__ = func.__dict__
        decorated.__doc__ = func.__doc__
        decorated.__module__ = func.__module__
        return decorated
    return decorate

Checksum_Hex, Checksum_Binary = 0, 1

def get_checksum(path, format=Checksum_Hex):
    """ Obtain the sha1 checksum of a file or directory.

    If path points to a directory, a collective checksum is calculated recursively for all files
    in the directory tree.
    @param path: Path to file or directory
    @param format: One of L{Checksum_Hex}, L{Checksum_Binary}.
    @raise ValueError: Invalid format.
    @return: If hexadecimal, a 40 byte hexadecimal digest. If binary, a 20byte binary digest.
    """
    if format not in (Checksum_Hex, Checksum_Binary):
        raise ValueError("Invalid format")

    def performSha1(path, shaObj):
        f = file(path)
        try:
            while True:
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

#{ Operating-system logic

Os_Linux = "linux"
Os_Windows = "windows"

OsCollection_Posix = (Os_Linux,)
Os_Posix = OsCollection_Posix   # Backwards-compat

def get_os():
    """ Get the current operating system.

    Lower-case strings are used to identify operating systems.
    @return: A pair of OS identifier and OS release (e.g. "xp") strings.
    """
    name, host, rls, ver, mach, proc = platform.uname()
    name = name.lower()
    return name, rls

def get_os_name():
    """ Get the name of the current operating system.
    
    This convenience function simply returns the first element of the tuple
    returned by L{get_os}.
    """
    return get_os()[0]
    
def get_os_version():
    """ Get the version of the current operating system.
    
    This convenience function simply returns the second element of the tuple
    returned by L{get_os}.
    """
    return get_os()[1]

#}

#{ Filesystem utilities

def replace_root(path, new_root, orig_root=None):
    """ Replace one root directory component of a pathname with another.
    @param path: The pathname.
    @param new_root: The root to replace the old root component with.
    @param orig_root: The original root component to replace, if C{None} the
    first directory component.
    @return: The new pathname.
    """
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
    relPath = path[len(orig_root):]
    return os.path.join(new_root, relPath)

def _raise_permissions(func):
    """ Raise PermissionsError upon filesystem access error. """
    def wrapper(*args, **kwds):
        try: return func(*args, **kwds)
        except EnvironmentError, err:
            if err.errno == errno.EACCES:
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
    def rmdir(path):
        chmodded = None
        if force:
            if get_os_name() == Os_Windows:
                mode = get_file_permissions(path)
                if not mode & stat.S_IWRITE:
                    mode |= stat.S_IWRITE
                chmod(path, mode)
            elif get_os_name() in OsCollection_Posix:
                # On POSIX, it is the permissions of the containing directory
                # that matters when deleting
                old_mode = get_file_permissions(os.path.dirname(path))
                if not old_mode & stat.S_IWRITE:
                    chmodded = os.path.dirname(path)
                    chmod(chmodded, old_mode | stat.S_IWRITE)

        try:
            assert not os.listdir(path), os.listdir(path)
            try: os.rmdir(path)
            except OSError, err:
                if not ignore_errors:
                    raise
        finally:
            if chmodded:
                chmod(chmodded, old_mode)
            
    def handle_err(dpath):
        if not force:
            raise PermissionsError(dpath)
        os.chmod(dpath, stat.S_IEXEC | stat.S_IREAD)
        return True
    
    if not os.path.exists(path):
        raise ValueError(path)

    if recurse:
        for dpath, dnames, fnames in walkdir(path, topdown=False, errorfunc=
                handle_err):
            for d in dnames:
                rmdir(os.path.join(dpath, d))
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

    This a simple convenience wrapper, for handling snags that may arise on different
    platforms.
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
def walkdir(path, errorfunc=None, topdown=True):
    """ Directory tree generator.
    
    This function works in much the same way as os.walk, but expands somewhat
    on that.
    @param path: Directory to traverse.
    @param errorfunc: Function to handle error when a directory can't be
    traversed. Return False from this to ignore directory.
    @param topdown: Traverse in topdown fashion?
    @raise PermissionsError: Missing permission to traverse directory.
    """
    if errorfunc is None:
        errorfunc = _walkdir_handle_err
        
    mode = get_file_permissions(path)
    if not mode & stat.S_IREAD:
        if not errorfunc(path):
            # Ignore directory
            return
    
    dnames, fnames = [], []
    for e in os.listdir(path):
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
def _copy_file(srcPath, dstPath, callback, totalBytes=None, readSoFar=long(0)):
    st = os.lstat(srcPath)
    sz = float(st.st_size)
    if totalBytes is None:
        totalBytes = sz
    if sz == 0:
        # Just create the destination file
        file(dstPath, "wb").close()
        callback(100)
    else:
        src = file(srcPath, "rb")
        dst = file(dstPath, "wb")
        try:
            while True:
                bytes = src.read(8192)
                dst.write(bytes)
                bytesRead = len(bytes)
                readSoFar += bytesRead
                callback(readSoFar / totalBytes * 100)
                if bytesRead < 8192:
                    break
        finally:
            src.close()
            dst.close()

    shutil.copystat(srcPath, dstPath)
    return readSoFar

def copy_file(sourcePath, destPath, callback=no_op):
    """ Copy a file.
    @param sourcePath: Source file path.
    @param destPath: Destination file path.
    @param callback: Optional callback to be invoked periodically with progress status.
    raise PermissionsError: Missing filesystem permissions.
    """
    _copy_file(sourcePath, destPath, callback)

@_raise_permissions
def remove_file(path, force=False):
    """ Remove a file.
    @param force: Force deletion of read-only file?
    @raise PermissionsError: Missing file-permissions.
    """
    chmodded = None
    if force:
        if get_os_name() == Os_Windows:
            chmod(path, stat.S_IWRITE)
        elif get_os_name() in OsCollection_Posix:
            # On POSIX, directory permissions matter
            dpath = os.path.dirname(path)
            old_mode = get_file_permissions(dpath)
            chmodded = dpath
            chmod(dpath, old_mode | stat.S_IWRITE)
    
    try: os.remove(path)
    finally:
        if chmodded:
            chmod(chmodded, old_mode)

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

@_raise_permissions
def copy_dir(sourcedir, destdir, callback=no_op, ignore=[], force=False):
    """ Copy a directory and its contents.
    @param sourcedir: Source directory.
    @param destdir: Destination directory.
    @param callback: Optional callback to be invoked periodically with progress status.
    @param ignore: Optional list of filename glob patterns to ignore.
    @param force: Force copying even if destination exists (implies deleting destination)?
    @raise DirectoryExists: The destination directory already exists (and C{force} is not
    specified).
    @raise PermissionsError: Missing permission to perform operation.
    """
    if os.path.exists(destdir):
        if not force:
            raise DestinationExists(destdir)
        remove_file_or_dir(destdir)

    def filter(names):
        """ Filter list of filesystem names in-place. When using os.walk, directories removed
        from the list won't be traversed. """
        for ptrn in ignore:
            for name in names[:]:
                if fnmatch.fnmatch(name, ptrn):
                    names.remove(name)
        return names

    os.makedirs(destdir)
    if platform.system() != "Windows":
        # Won't work on Windows
        shutil.copystat(sourcedir, destdir)
    allBytes = 0
    for dpath, dnames, fnames in walkdir(sourcedir):
        for d in filter(dnames):
            allBytes += 1
        for f in filter(fnames):
            allBytes += os.lstat(os.path.join(dpath, f)).st_size

    # First invoke the callback with a progress of 0
    callback(0)
    bytes = 0
    allBytes = float(allBytes)
    # Use a long to make sure it can hold a long enough number
    readSoFar = long(0)
    for dpath, dnames, fnames in walkdir(sourcedir):
        for d in filter(dnames):
            srcPath = os.path.join(dpath, d)
            dstPath = replace_root(srcPath, destdir, sourcedir)
            os.mkdir(dstPath)
            if platform.system() != "Windows":
                # Won't work on Windows
                shutil.copystat(srcPath, dstPath)
            readSoFar += 1
            callback(readSoFar / allBytes * 100)
        for f in filter(fnames):
            srcPath = os.path.join(dpath, f)
            dstPath = replace_root(srcPath, destdir, sourcedir)
            readSoFar = _copy_file(srcPath, dstPath, callback, allBytes, readSoFar)

def create_tempfile(suffix="", prefix="tmp", close=True, content=None,
        encoding=None):
    """ Create temporary file.
    
    The file is opened in R/W mode.
    @param suffix: Optional filename suffix.
    @param prefix: Optional filename prefix.
    @param close: Close the file after creating it?
    @param content: Optional content to write to file.
    @param encoding: Specify text encoding for file.
    @return: If C{close} path to created temporary file, else temporary file. """
    import tempfile
    (fd, fname) = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    # File should not be automatically deleted
    os.close(fd)
    
    if not close or content:
        # Open file directly instead of using fdopen, since the latter will return
        # a file with a bogus name
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
        chksum0, chksum1 = get_checksum(path0, format=Checksum_Binary), get_checksum(
                path1, format=Checksum_Binary)
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
        contents1 = [e for e in os.listdir(os.path.join(dir1, reldir)) if not e in ignore]

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
                        sys.stderr.write("Mismatched: %r, %r\n" % (s0[1:], s1[1:]))
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
    """ Resolve name of executable into absolute path.
    @raise NotFound: The executable was not found in path.
    """
    import os.path
    path = os.environ["PATH"].split(os.pathsep)
    if get_os_name() == Os_Windows:    # pragma: optional
        import win32api, pywintypes
        try: return win32api.FindExecutable(executable)[1]
        except pywintypes.error: pass
    else:
        for d in path:
            try:
                exepath = os.path.join(d, executable)
                if os.access(exepath, os.X_OK):
                    return exepath
            except OSError:
                pass
    raise NotFound(executable)

#}
