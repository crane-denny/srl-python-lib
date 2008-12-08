""" Unit testing functionality. """
import unittest, os.path, sys, shutil, tempfile
import warnings

import srllib.util
from mock import Mock

# This flag makes unittest omit our test methods in failure tracebacks, like the standard test methods.
__unittest = True

class TestCase(unittest.TestCase):
    """ Extended TestCase baseclass.
    
    @note: In the setUp method, the original working directory is registered
    so it can be restored in tearDown. 
    @ivar _orig_attrs: Dictionary of object attributes to reset on teardown.
    @ivar _tempfiles: List of temporary files to delete on teardown.
    @ivar _tempdirs: List of temporary directories to delete on teardown.
    """
    def __init__(self, *args, **kwds):
        unittest.TestCase.__init__(self, *args, **kwds)

    def setUp(self):
        # from conduit import mythreading
        # mythreading.registerExceptionHandler(self._exception_handler)
        (self.__connections, self._orig_attrs, self._tempfiles,
            self._tempdirs) = [], {}, [], []
                
        # Register the original working directory so this can be restored
        # at the end of the test.
        self.__cwd = os.getcwd()

    def tearDown(self):
        if self.__cwd is not None:
            os.chdir(self.__cwd)
            
        for k, v in self._orig_attrs.items():
            obj, attr = k
            val = v
            setattr(obj, attr, val)
        for sig, slt in self.__connections:
            sig.disconnect(slt)
        for ftemp in self._tempfiles:
            if isinstance(ftemp, file):
                ftemp.close()
                fname = ftemp.name
            else:
                fname = ftemp
            try: os.remove(fname)
            except OSError: pass
        for dtemp in self._tempdirs:
            if not os.path.exists(dtemp):
                continue
            srllib.util.remove_dir(dtemp, force=True, recurse=True)

        # Reset Mock register
        Mock.mockInstances.clear()

    def assertNot(self, val, msg=None):
        self.assert_(not val, msg=msg)
        
    def assertStrEqual(self, lhs, rhs, msg=None):
        self.assertEqual(str(lhs), str(rhs), msg)

    def assertStrNotEqual(self, lhs, rhs, msg=None):
        self.assertNotEqual(str(lhs), str(rhs), msg)

    def assertSortedEqual(self, lhs, rhs, msg=None):
        lhs = list(lhs)
        rhs = list(rhs)
        lhs.sort()
        rhs.sort()
        self.assertSeqEqual(lhs, rhs, msg)

    def assertSeqEqual(self, lhs, rhs, msg=None):
        if not isinstance(lhs, tuple):
            lhs = tuple(lhs)
        if not isinstance(rhs, tuple):
            rhs = tuple(rhs)
        if not lhs == rhs:
            raise self.failureException, msg or "%r != %r" % (lhs, rhs)

    def assertIs(self, lhs, rhs, msg=None):
        if not lhs is rhs:
            raise self.failureException, msg or "%r is not %r" % (lhs, rhs)

    def assertIsNot(self, lhs, rhs, msg=None):
        if lhs is rhs:
            raise self.failureException, msg or "%r is %r" % (lhs, rhs)

    def assertIn(self, val, seq, msg=None):
        if not val in seq:
            raise self.failureException, msg or "%r not in %r" % (val, seq)

    def assertNotIn(self, val, seq, msg=None):
        if val in seq:
            raise self.failureException, msg or "%r in %r" % (val, seq)

    def assertGreaterThan(self, lhs, rhs, msg=None):
        if lhs <= rhs:
            raise self.failureException, msg or "%r <= %r" % (lhs, rhs)

    def assertLessThan(self, lhs, rhs, msg=None):
        if lhs >= rhs:
            raise self.failureException, msg or "%r >= %r" % (lhs, rhs)

    def assertGreaterOrEqual(self, lhs, rhs, msg=None):
        if lhs < rhs:
            raise self.failureException, msg or "%r < %r" % (lhs, rhs)

    def assertLessOrEqual(self, lhs, rhs, msg=None):
        if lhs > rhs:
            raise self.failureException, msg or "%r > %r" % (lhs, rhs)

    def _connect_to(self, signal, slot):
        signal.connect(slot)
        self.__connections.append((signal, slot))

    def _set_attr(self, obj, attr, val):
        """ Change an attribute of some object.
        
        The original attribute of the object is recorded, so that it can be restored after the test.
        @param obj: The object.
        @param attr: Name of attribute to change
        @param val: The intended value of the attribute
        """
        if not (obj, attr) in self._orig_attrs:
            self._orig_attrs[(obj, attr)] = getattr(obj, attr)
        setattr(obj, attr, val)

    def _set_module_attr(self, mdl, attr, val):
        """ Change the attribute of a module.
        
        The original attribute of the module is recorded, so that it can be restored after the test.
        @param mdl: Name of module or module.
        @param attr: Name of attribute to change
        @param val: The intended value of the attribute
        """
        if isinstance(mdl, basestring):
            try:
                fromList = [mdl.rsplit(".", 1)[1]]
            except IndexError:
                fromList = []
            m = __import__(mdl, None, None, fromList)
        else:
            m = mdl

        self._set_attr(m, attr, val)

    def _restore_attr(self, obj, attr):
        val = self._orig_attrs.pop((obj, attr))
        setattr(obj, attr, val)

    def _restore_module_attr(self, mdl, attr):
        if isinstance(mdl, basestring):
            try:
                fromList = [mdl.rsplit(".", 1)[1]]
            except IndexError:
                fromList = []
            m = __import__(mdl, None, None, fromList)
        else:
            m = mdl
        self._restore_attr(m, attr)
    
    def _exception_handler(self, exception):
        raise exception

    def _get_datapath(self, relpath, abs=False):
        """ For subclasses: Get path to file in "Data" directory.
        @param abs: Return absolute path?
        """
        dpath = os.path.join("Data", relpath)
        if abs:
            dpath = os.path.abspath(dpath)
        return dpath

    def _get_bindatapath(self, relPath):
        if relPath.count(os.path.sep) > 1:
            parDir, remaining = relPath.split(os.path.sep, 1)
        else:
            parDir, remaining = relPath, ""
        os_name = srllib.util.get_os_name()
        if os_name == srllib.util.Os_Windows:
            parDir += "-win"
        elif os_name == srllib.util.Os_Linux:
            parDir += "-linux"
        '''
        elif Os in Darwin:
            parDir += "-osx"
        '''
        ret = os.path.join("Data", parDir, remaining)
        return ret

    def _get_tempfname(self, *args, **kwds):
        ftemp = srllib.util.create_tempfile(*args, **kwds)
        self._tempfiles.append(ftemp)
        return ftemp

    def _get_tempfile(self, *args, **kwds):
        ftemp = srllib.util.create_tempfile(close=False, *args, **kwds)
        self._tempfiles.append(ftemp)
        return ftemp

    def _get_tempdir(self, *args, **kwds):
        """ Create temporary directory that is removed on tearDown. """
        dtemp = tempfile.mkdtemp(*args, **kwds)
        self._tempdirs.append(dtemp)
        return dtemp
    
    def _get_privattr(self, obj, name, classname=None):
        """ Get a private (name mangled) attribute of an object.
        @param classname: Optionally specify the class in question where the
        private attribute is set. Otherwise it is deduced from the object's
        class.
        """
        mangled_name = self.__mangle_priv(obj, classname, name)
        return getattr(obj, mangled_name)
    
    def _set_privattr(self, obj, name, val, assert_exists=True, classname=None):
        """ Set a private (name mangled) attribute of an object.
        @param assert_exists: Assert that the attribute already exists?
        @param classname: Optionally specify the class in question where the
        private attribute is set. Otherwise it is deduced from the object's
        class.
        """
        mangled_name = self.__mangle_priv(obj, classname, name)
        if assert_exists:
            getattr(obj, mangled_name)
        setattr(obj, mangled_name, val)

    def __mangle_priv(self, obj, classname, name):
        if classname is None:
            classname = obj.__class__.__name__
        if not classname.startswith("_"):
            classname = "_" + classname
        if not name.startswith("__"):
            name = "__" + name
        else:
            warnings.warn("specifying private prefix is deprecated",
                    DeprecationWarning, stacklevel=2)

        return "%s%s" % (classname, name)

class TestPersistent(TestCase):
    pass

import stat

def _sig(st):
    return (stat.S_IFMT(st.st_mode), st.st_size, stat.S_IMODE(st.st_mode), st.st_uid, st.st_gid)

def compare_dirs(dir0, dir1, shallow=True, ignore=[]):
    """ Check that the contents of two directories match.

    Contents that mismatch and content that can't be found in one directory or can't be checked somehow are returned
    separately.
    @param shallow: Just check the stat signature instead of reading content
    @param ignore: Names of files(/directories) to ignore
    @return: Pair of mismatched and failed pathnames, respectively
    """
    mismatch = []
    error = []
    if len(os.listdir(dir0)) == 0:
        return mismatch, os.listdir(dir1)
    assert os.path.exists(dir0), "%s does not exist" % dir0
    assert os.path.exists(dir1), "%s does not exist" % dir1
    
    if dir0[-1] != os.path.sep:
        dir0 = dir0 + os.path.sep
    for dpath, dnames, fnames in os.walk(dir0):
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
                        chksum0, chksum1 = (srllib.util.get_checksum(path0),
                                srllib.util.get_checksum(path1))
                        mismatched = srllib.util.get_checksum(path0) != \
                                srllib.util.get_checksum(path1)
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
                sys.stderr.write("Error: %s\n" % relPath)
                error.append(relPath)

    return mismatch, error

def _get_tests(specified):
    specificTests = [t for t in specified.split(",") if t]
    from glob import glob
    if not specified:
        return [os.path.splitext(os.path.basename(path))[0] for path in glob("test*.py")]

    tests = []
    for t in specificTests:
        # Prepend "test" to specified tests if necessary
        if not t.startswith("test"):
            t = "test" + t
        tests.append(t)
    return tests

'''
def _analyzePkg(pkg, rslts, ignore):
    """ Find all sub-modules of a package and analyze them. """
    import imp
    pdir = os.path.dirname(pkg.__file__)
    pkgName = pkg.__name__
    if "." in pkgName:
        # A sub package
        pkgName = pkg.__name__.split(".", 1)[1]
        topPkg = False
    else:
        topPkg = True

    for e in os.listdir(pdir):
        abspath = os.path.join(pdir, e)
        if os.path.splitext(e)[1] == ".py" or os.path.isdir(abspath) and \
                os.path.isfile(os.path.join(abspath, "__init__.py")):
            if os.path.isfile(abspath):
                if e == "__init__.py":
                    continue
                name = os.path.splitext(e)[0]
            else:
                name = e
            if not topPkg:
                qname = "%s.%s" % (pkgName, name)
            else:
                qname = name
            if qname in ignore:
                continue

            f, p, d = imp.find_module(name, pkg.__path__)
            try:
                m = imp.load_module("%s.%s" % (pkg.__name__, name), f, p, d)
            finally:
                if f is not None:
                    f.close()
            f, s, i, n, h  = coverage.analysis2(m)
            rslts[m.__name__] = (s, n, h)

            if os.path.isdir(abspath):
                # Recurse over sub-package
                _analyzePkg(m, rslts, ignore)

def _analyzeCoverage(package_name, tests, infer, ignore):
    """ Analyze code coverage by tests. """
    rslts = {}
    if not infer:
        pkg = __import__(package_name)
        _analyzePkg(pkg, rslts, ignore)
    else:
        for t in tests:
            # Get only the name of the test module, the specification may be referring to
            # a module attribute
            t = t.split(".", 1)[0]
            assert t.startswith("test")

            # See if the test specifies which modules it involves
            testMod = __import__(t)
            modules = []
            if hasattr(testMod, "_Test_Modules"):
                modules = getattr(testMod, "_Test_Modules")
            else:
                fullMname = t[4:]
                modules.append(t[4:])
                    
            for fullMname in modules:
                if fullMname in ignore:
                    continue

                if "." in fullMname:
                    mname = fullMname.rsplit(".", 1)[1]
                else:
                    mname = fullMname
                m = __import__("%s.%s" % (package_name, fullMname), globals(), locals(), [mname])
                f, s, i, n, h = coverage.analysis2(m)
                rslts[fullMname] = (s, n, h)

    totalStatements = totalNe = 0
    mnames = rslts.keys()
    mnames.sort()
    for mname in mnames:
        statements, notExecuted, formatted = rslts[mname]
        cov = 1.0 - len(notExecuted) / float(len(statements))
        print "%s:\n%s\nNo. statements: %d\nNot executed: %s\nCoverage: %f\n" % \
                (mname, "-" * (len(mname) + 1), len(statements), formatted, cov)
        totalStatements += len(statements)
        totalNe += len(notExecuted)
    print "Total coverage: %f" % (1.0 - totalNe / float(totalStatements),)
'''

def _error(msg):
    sys.stderr.write("%s\n" % msg)
    sys.exit(1)

def run_tests(package_name, gui=False, test_module=None):
    """ Use L{nose} for discovering/running tests.

    After finishing, sys.exit is called with the success status.
    @param package_name: Name of package that is tested. Used for analyzing
    coverage by tests.
    @param gui: Do the tests involve GUI code?
    @param test_module: Optionally module containing tests.
    """
    import optparse, nose.core

    if gui:
        import srllib.testing.qtgui, srllib.qtgui
        srllib.testing.qtgui.GuiTestCase.QApplicationClass = srllib.qtgui.Application
    sys.argv.append("--cover-package=%s" % (package_name,))
    # Can't find a better way to make nose ignore this function :(
    sys.argv.append("--exclude=%s" % ("run_tests",))

    class TestCollector(nose.core.TestCollector):
        def loadtests(self):
            for t in self.loader.loadTestsFromDir(os.getcwd()):
                yield t

    try:
        r = nose.run(module=test_module)
    finally:
        '''
        if gui:
            from PyQt4 import QtGui
            QtGui.qApp.quit()
            QtGui.qApp.processEvents()
            '''
        pass

    sys.exit(r)

from unittest import main
