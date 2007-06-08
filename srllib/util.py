""" Various utility functionality. """
import stat, shutil, os.path, imp, platform, fnmatch, sys, errno
try: import hashlib
except ImportError: import sha

from error import *

def noOp(*args, **kwds):
    """ Utility no-op function that accepts any arguments/keywords. """
    pass

Checksum_Hex, Checksum_Binary = 0, 1

def getChecksum(path, format=Checksum_Hex):
    """ Obtain the sha1 checksum of a file or directory.

    If path points to a directory, a collective checksum is calculated recursively for all files
    in the directory tree.
    @param path: Path to file or directory
    @param format: One of L{Checksum_Hex}, L{Checksum_Binary}.
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
        for dpath, dnames, fnames in walkDir(path):
            for fname in fnames:
                performSha1(os.path.join(dpath, fname), shaObj)
    else:
        performSha1(path, shaObj)

    return shaMthd()

def getModule(name, path):
    """ Search for a module along a given path and load it.
    @param name: Module name.
    @param path: Path of directories to search.
    @raise ValueError: Module not found.
    """
    try:
        file_, fname, extra = imp.find_module(name, path)
        mod = imp.load_module(name, file_, fname, extra)
    except ImportError:
        raise ValueError(name)
    return mod

#{ Filesystem utilities

def replaceRoot(path, newRoot, origRoot=None):
    """ Replace one root directory component of a pathname with another.
    @param path: The pathname.
    @param newRoot: The root to replace the old root component with.
    @param origRoot: The original root component to replace, if None the filesystem root.
    @return: The new pathname.
    """
    if origRoot is None:
        if Os in Posix:
            origRoot = "/"
        elif Os in Windows:
            origRoot = path.split(os.path.sep, 1)[0] + os.path.sep
    else:
        origRoot = os.path.normpath(origRoot)
        origRoot += os.path.sep
    relPath = path[len(origRoot):]
    return os.path.join(newRoot, relPath)

def _raisePermissions(func):
    """ Raise PermissionsError upon filesystem access error. """
    def wrapper(*args, **kwds):
        try: return func(*args, **kwds)
        except EnvironmentError, err:
            if err.errno == errno.EACCES:
                raise PermissionsError(err.message)
            else:
                raise

    return wrapper

class DirNotEmpty(SimulaError):
    pass

@_raisePermissions
def removeDir(path, ignoreErrors=False, force=False, recurse=True):
    """ Remove directory, optionally a whole directory tree (recursively).
    
    @param ignoreErrors: Ignore failed deletions?
    @param force: On Windows, force deletion of read-only files?
    @param recurse: Delete also contents, recursively?
    @raise PermissionsError: Missing file-permissions.
    @raise DirNotEmpty: Directory was not empty, and recurse was not specified.
    """
    def rmdir(path):
        if force and platform.system() == "Windows":
            # On POSIX, it is the permissions of the containing directory that matters when deleting
            mode = getFilePermissions(path)
            if not mode & stat.S_IWRITE:
                mode |= stat.S_IWRITE
            chmod(path, mode)
        try: os.rmdir(path)
        except OSError, err:
            if not ignoreErrors:
                raise

    if recurse:
        for dpath, dnames, fnames in os.walk(path, topdown=False):
            for d in dnames:
                rmdir(os.path.join(dpath, d))
            for f in fnames:
                removeFile(os.path.join(dpath, f), force=force)
    else:
        if os.listdir(path):
            raise DirNotEmpty
    rmdir(path)

rmtree = removeDir  # Backwards-compat

def getFilePermissions(path):
    """ Get permissions flags (bitwise) for a file/directory.
    
    Links are not dereferenced.
    """
    return stat.S_IMODE(os.lstat(path).st_mode)

@_raisePermissions
def moveFile(src, dest, force=False):
    """ Move a file, cross-platform safe.

    This a simple convenience wrapper, for handling snags that may arise on different
    platforms.
    @param force: On Windows, overwrite write-protected destination?
    """
    if platform.system() == "Windows" and os.path.isfile(dest):
        # Necessary on Windows
        if force:
            dstMode = getFilePermissions(dst)
            if not dstMode & stat.S_IWRITE:
                chmod(dest, dstMode | stat.S_IWRITE)
        os.remove(dest)
    shutil.move(src, dest)

def cleanPath(path):
    """ Return a clean, absolute path. """
    return os.path.abspath(os.path.normpath(path))

def walkDir(path):
    """ Wrapper around os.walk which checks whether we are permitted to traverse.
    @raise PermissionsError: Missing permission to traverse directory.
    """
    if not os.access(path, os.R_OK):
        raise PermissionsError(path)
    for dpath, dnames, fnames in os.walk(path):
        for d in dnames:
            if not os.access(os.path.join(dpath, d), os.R_OK):
                raise PermissionsError(os.path.join(dpath, d))
        yield dpath, dnames, fnames

@_raisePermissions
def _copyFile(srcPath, dstPath, callback, totalBytes=None, readSoFar=long(0)):
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

class PermissionsError(SimulaError):
    """ Filesystem permissions error.
    @ivar reason: Original reason for error.
    """
    def __init__(self, path, reason=None):
        SimulaError.__init__(self, path)
        self.reason = reason

def copyFile(sourcePath, destPath, callback=noOp):
    """ Copy a file.
    @param sourcePath: Source file path.
    @param destPath: Destination file path.
    @param callback: Optional callback to be invoked periodically with progress status.
    raise PermissionsError: Missing filesystem permissions.
    """
    _copyFile(sourcePath, destPath, callback)

@_raisePermissions
def removeFile(path, force=False):
    """ Remove a file.
    @raise PermissionsError: Missing file-permissions.
    """
    os.remove(path)

def removeFileOrDir(path, force=False, recurse=True):
    """ Remove a filesystem object, whether it is a file or a directory.
    @param force: On Windows, force deletion of read-only files?
    @param recurse: Delete recursively, if a directory?
    @raise PermissionsError: Missing file-permissions.
    @raise DirNotEmpty: Directory was not empty, and recurse was not specified.
    """
    if os.path.isdir(path):
        removeDir(path, force=force, recurse=recurse)
    else:
        removeFile(path, force=force)

class DestinationExists(SimulaError):
    pass

@_raisePermissions
def copyDir(sourceDir, destDir, callback=noOp, ignore=[], force=False):
    """ Copy a directory and its contents.
    @param sourceDir: Source directory.
    @param destDir: Destination directory.
    @param callback: Optional callback to be invoked periodically with progress status.
    @param ignore: Optional list of filename glob patterns to ignore.
    @param force: Force copying even if destination exists (implies deleting destination)?
    @raise DirectoryExists: The destination directory already exists (and C{force} is not
    specified).
    @raise PermissionsError: Missing permission to perform operation.
    """
    if os.path.exists(destDir):
        if not force:
            raise DestinationExists(destDir)
        removeFileOrDir(destDir)

    def filter(names):
        """ Filter list of filesystem names in-place. When using os.walk, directories removed
        from the list won't be traversed. """
        for ptrn in ignore:
            for name in names[:]:
                if fnmatch.fnmatch(name, ptrn):
                    names.remove(name)
        return names

    os.makedirs(destDir)
    if platform.system() != "Windows":
        # Won't work on Windows
        shutil.copystat(sourceDir, destDir)
    numFiles = 0
    allBytes = 0
    for dpath, dnames, fnames in walkDir(sourceDir):
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
    for dpath, dnames, fnames in walkDir(sourceDir):
        for d in filter(dnames):
            srcPath = os.path.join(dpath, d)
            dstPath = replaceRoot(srcPath, destDir, sourceDir)
            os.mkdir(dstPath)
            if platform.system() != "Windows":
                # Won't work on Windows
                shutil.copystat(srcPath, dstPath)
            readSoFar += 1
            callback(readSoFar / allBytes * 100)
        for f in filter(fnames):
            srcPath = os.path.join(dpath, f)
            dstPath = replaceRoot(srcPath, destDir, sourceDir)
            readSoFar = _copyFile(srcPath, dstPath, callback, allBytes, readSoFar)

def createTemporaryFile(suffix="", prefix="tmp", close=True):
    """ Create temporary file.
    @param suffix: Optional filename suffix.
    @param prefix: Optional filename prefix.
    @param close: Close the file after creating it?
    @return: If close path to created temporary file, else temporary file. """
    import tempfile
    (fd, fname) = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    # File should not be automatically deleted
    os.close(fd)
    if close:
        return fname
    f = file(fname, "wb+")
    return f

def createFile(name, content="", binary=False):
    """ Create a file, with optional content.
    @param name: Filename.
    @param content: Optional content to write to file.
    @param binary: Create file in binary mode (makes a difference on Windows)?
    @return: Path to created file.
    """
    mode = "w"
    if binary:
        mode += "b"
    f = file(name, mode)
    try:
        if content:
            f.write(content)
    finally:
        f.close()

    return name

def _sig(st):
    return (stat.S_IFMT(st.st_mode), st.st_size, stat.S_IMODE(st.st_mode), st.st_uid, st.st_gid)

def compareDirs(dir0, dir1, shallow=True, ignore=[], fileCheckFunc=None):
    """ Check that the contents of two directories match.

    Contents that mismatch and content that can't be found in one directory or can't be checked somehow are returned
    separately.
    @param shallow: Just check the stat signature instead of reading content
    @param ignore: Names of files(/directories) to ignore
    @param fileCheckFunc: Optionally provide function for deciding whether two files are alike.
    @return: Pair of mismatched and failed pathnames, respectively
    """
    def checkFiles(file0, file1):
        return getChecksum(file0, format=Checksum_Binary) == getChecksum(file1, format=Checksum_Binary)

    if fileCheckFunc is None:
        fileCheckFunc = checkFiles
    mismatch = []
    error = []
    if len(os.listdir(dir0)) == 0:
        return mismatch, os.listdir(dir1)
    if not os.path.exists(dir0):
        raise ValueError("First directory missing: '%s'" % (dir0,))
    if not os.path.exists(dir1):
        raise ValueError("Second directory missing: '%s'" % (dir1,))
    
    if dir0[-1] != os.path.sep:
        dir0 = dir0 + os.path.sep
    for dpath, dnames, fnames in walkDir(dir0):
        for ign in ignore:
            while ign in dnames:
                dnames.remove(ign)
            while ign in fnames:
                fnames.remove(ign)

        relDir = dpath[len(dir0):]
        assert relDir != dpath, dpath
        
        contents0 = dnames + fnames
        contents1 = [e for e in os.listdir(os.path.join(dir1, relDir)) if not e in ignore]

        lnth0, lnth1 = len(contents0), len(contents1)
        if lnth0 < lnth1:
            for name in contents1:
                if name not in contents0:
                    error.append(os.path.join(relDir, name))
        
        import stat
        for name in contents0:
            relPath = os.path.join(relDir, name)
            try:
                path0, path1 = os.path.join(dir0, relPath), os.path.join(dir1, relPath)
                st0, st1 = os.lstat(path0), os.lstat(path1)
                mode0, mode1 = stat.S_IMODE(st0.st_mode), stat.S_IMODE(st1.st_mode)
                mismatched = False
                s0, s1 = _sig(st0), _sig(st1)
                if name in fnames:
                    if s0 != s1:
                        sys.stderr.write("%s mismatched because %r != %r\n" % (path1, s0, s1))
                        mismatched = True
                        shutil.copytree(dir0, "/tmp/mismatch")
                    elif not shallow:
                        chksum0, chksum1 = getChecksum(path0), getChecksum(path1)
                        mismatched = getChecksum(path0) != getChecksum(path1)
                        if mismatched:
                            sys.stderr.write("%s mismatched against %s because %s != %s\n" % (path0, path1, chksum0, chksum1))
                else:
                    assert name in dnames
                    mismatched = s0[2:] != s1[2:]   # Ignore format and size
                    if mismatched:
                        # No need to traverse this directory
                        sys.stderr.write("Mismatched: %r, %r\n" % (s0[1:], s1[1:]))
                        dnames.remove(name)
                if mismatched:
                    mismatch.append(relPath)
            except OSError:
                if name in dnames:
                    dnames.remove(name)
                error.append(relPath)

    return mismatch, error

@_raisePermissions
def chmod(path, mode, recursive=False):
    """ Wrapper around os.chmod, which allows for recursive modification of a directory.
    @param path: Path to modify.
    @param mode: New permissions mode.
    @param recursive: Apply recursively, if directory?
    @raise PermissionsError: Missing file-permissions.
    """
    madeExec = []

    def _chmod(path, fixExec=False):
        newMode = mode
        if fixExec and os.path.isdir(path) and not mode & stat.S_IEXEC:
            # Make the directory accessible
            newMode |= stat.S_IEXEC
            madeExec.append(path)

        os.chmod(path, newMode)

    if recursive and os.path.isdir(path):
        for dpath, dnames, fnames in walkDir(path):
            _chmod(dpath, fixExec=True)

            for d in dnames[:]:
                # Chmod empty dirs now
                if not os.listdir(os.path.join(dpath, d)):
                    _chmod(os.path.join(dpath, d))
                    dnames.remove(d)
            for f in fnames:
                _chmod(os.path.join(dpath, f))

        # Now finalize the executable bit in depth-first fashion
        for dpath in reversed(madeExec):
            _chmod(dpath)
    else:
        _chmod(path)

#}
