# -*- coding: utf-8 -*-
""" Test the util module. """
import os.path, stat, codecs

from srllib.testing import *
from srllib import util
import srllib.error as _srlerror

class FileSystemTest(TestCase):
    """ Test filesystem utility functions. """
    def test_movefile(self):

        # There might be a problem moving a file onto another, we are testing
        # this case as well since the destination already exists
        dstDir = self._get_tempdir()
        src, dst = self._get_tempfile(), util.create_file(os.path.join(dstDir, "test"))
        try: src.write("Test")
        finally: src.close()

        if util.get_os()[0] == util.Os_Windows:
            util.chmod(dst, 0)
        else:
            util.chmod(dstDir, 0)
        self.assertRaises(util.PermissionsError, util.move_file, src.name, dst)
        if util.get_os()[0] == util.Os_Windows:
            util.chmod(dst, 0700)
        else:
            util.chmod(dstDir, 0700)
        util.move_file(src.name, dst)
        f = file(dst)
        try: txt = f.read()
        finally: f.close()
        self.assertEqual(txt, "Test")
        self.assertNot(os.path.exists(src.name))

    def test_remove_dir(self):
        dpath = self.__create_dir()
        self.assertRaises(util.DirNotEmpty, util.remove_dir, dpath, recurse=False)
        util.remove_dir(dpath, recurse=True)
        self.assertNot(os.path.exists(dpath))

        # Test removing an empty dir
        dpath = self._get_tempdir()
        util.remove_dir(dpath, recurse=False)
        self.assertNot(os.path.exists(dpath))
        
    def test_remove_dir_force(self):
        """ Test removing directory with read-only contents. """
        dpath = self.__create_dir()
        util.chmod(dpath, 0, recursive=True)
        util.remove_dir(dpath, force=True)
        self.assertNot(os.path.exists(dpath))
        
    def test_remove_dir_missing(self):
        """ Test removing a missing directory. """
        self.assertRaises(ValueError, util.remove_dir, "nosuchdir")

    def test_copydir(self):
        """ Test copying a directory.

        When a directory is copied, the client callback should be called periodically with
        progress status.
        """
        def callback(progress):
            self.__progress.append(progress)

        dpath = self.__create_dir()
        dstDir = self._get_tempdir()
        self.assertRaises(util.DestinationExists, util.copy_dir, dpath, dstDir)

        # Try forcing deletion of existing directory

        os.mkdir(os.path.join(dstDir, "testdir"))
        # Remove only write permission
        if util.get_os()[0] == util.Os_Windows:
            util.chmod(os.path.join(dstDir, "testdir"), 0500)
        else:
            util.chmod(dstDir, 0500)
        # Make sure we can access the directory (requires the correct
        # permissions on dstDir)
        assert os.path.exists(os.path.join(dstDir, "testdir"))
        # This should fail, because the conflicting directory is protected from
        # deletion
        self.assertRaises(util.PermissionsError, util.copy_dir, dpath,
                os.path.join(dstDir, "testdir"), force=True)
        if util.get_os()[0] == util.Os_Windows:
            util.chmod(os.path.join(dstDir, "testdir"), 0700)
        else:
            util.chmod(dstDir, 0700)
        util.copy_dir(dpath, dstDir, force=True)

        util.remove_dir(dstDir, recurse=True)
        self.__progress = []
        util.copy_dir(dpath, dstDir, callback=callback)
        self.assertEqual(compare_dirs(dpath, dstDir), ([], []))
        self.assertEqual(self.__progress[0], 0.0)
        self.assertEqual(self.__progress[-1], 100.0)

        # Test ignoring certain files
        dpath = self._get_tempdir()
        os.mkdir(os.path.join(dpath, ".svn"))
        util.create_file(os.path.join(dpath, "test"))
        dstDir = self._get_tempdir()
        util.copy_dir(dpath, dstDir, ignore=[".*"], force=True)
        self.assertEqual(os.listdir(dstDir), ["test"])

    def test_copy_noperm(self):
        """ Test copying a directory with missing permissions. """
        dpath0, dpath1 = self.__create_dir(), self._get_tempdir()
        if util.get_os()[0] != util.Os_Windows:
            # Can't remove read permission on Windows
            util.chmod(dpath0, 0)
            self.assertRaises(util.PermissionsError, util.copy_dir, dpath0,
                    dpath1, force=True)
            util.chmod(dpath0, 0700)
            # Test directory permissions
            util.chmod(os.path.join(dpath0, "testdir"), 0000)
            self.assertRaises(util.PermissionsError, util.copy_dir, dpath0,
                    dpath1, force=True)
            util.chmod(os.path.join(dpath0, "testdir"), 0700)
            # Test file permissions
            util.chmod(os.path.join(dpath0, "test"), 0000)
            self.assertRaises(util.PermissionsError, util.copy_dir, dpath0,
                    dpath1, force=True)

    def test_copyfile(self):
        src, dst = self._get_tempfile(), self._get_tempfname()
        try: src.write("Test")
        finally: src.close()
        util.copy_file(src.name, dst)
        f = file(dst)
        try: txt = f.read()
        finally: f.close()
        self.assertEqual(txt, "Test")

    def test_create_tempfile(self):
        fname = self.__create_tempfile()
        try: self.assert_(isinstance(fname, basestring))
        finally: os.remove(fname)
        file_ = self.__create_tempfile(close=False)
        try: self.assert_(isinstance(file_, file))
        finally:
            file_.close()
            os.remove(file_.name)
        file_ = self.__create_tempfile(close=False, content="Test")
        try:
            txt = file_.read()
            self.assertEqual(txt, "Test")
            # XXX: On Windows, we have to write from the beginning of file for
            # some reason, otherwise IOError is raised
            file_.seek(0)
            file_.write(txt + "\nTest")
            file_.seek(0)
            self.assertEqual(file_.read(), "Test\nTest")
        finally: file_.close()
        
    def test_create_tempfile_invalid_encoding(self):
        self.assertRaises(UnicodeDecodeError, self.__create_tempfile,
                content="æøå", encoding="ascii")

    def test_chmod(self):
        dpath = self.__create_dir()
        util.chmod(dpath, 0)
        mode = stat.S_IMODE(os.stat(dpath).st_mode)
        if util.get_os()[0] == util.Os_Windows:
            # Impossible to remove rx permissions on Windows
            self.assertNot(mode & stat.S_IWRITE)
        else:
            self.assertEqual(mode, 0)
            self.assertRaises(util.PermissionsError, util.chmod, dpath, 0,
                    recursive=True)
        util.chmod(dpath, 0700)
        util.chmod(dpath, 0000, recursive=True)
        util.chmod(dpath, 0700)
        filemode = stat.S_IMODE(os.stat(os.path.join(dpath, "test")).st_mode)
        dirmode = stat.S_IMODE(os.stat(os.path.join(dpath, "testdir")).st_mode)
        if util.get_os()[0] == util.Os_Windows:
            self.assertNot(filemode & (stat.S_IWRITE | stat.S_IEXEC))
            self.assertNot(dirmode & stat.S_IWRITE)
        else:
            self.assertEqual(filemode, 0)
            self.assertEqual(dirmode, 0)
    
    def test_chmod_recursive(self):
        """ Test chmod in recursive mode. """
        dpath = self._get_tempdir()
        fpath = util.create_file(os.path.join(dpath, "file"))
        os.mkdir(os.path.join(dpath, "subdir"))
        # Set executable so the directory can be traversed
        mode = stat.S_IREAD | stat.S_IEXEC
        util.chmod(dpath, mode, True)
        self.assertEqual(util.get_file_permissions(dpath), mode)
        for e in os.listdir(dpath):
            self.assertEqual(util.get_file_permissions(os.path.join(dpath, e)),
                    mode)

    def test_walkdir(self):
        entered = []
        root = self.__create_dir()
        for dpath, dnames, fnames in util.walkdir(root):
            entered.append(dpath)
        self.assertEqual(entered, [root, os.path.join(root, "testdir")])

    def test_remove_file(self):
        dpath = self._get_tempdir()
        fpath = util.create_file(os.path.join(dpath, "test"))
        if util.get_os()[0] == util.Os_Windows:
            util.chmod(fpath, 0)
        else:
            util.chmod(dpath, 0)
        self.assertRaises(util.PermissionsError, util.remove_file, fpath)
        if util.get_os()[0] == util.Os_Windows:
            util.chmod(fpath, 0700)
        else:
            util.chmod(dpath, 0700)
        util.remove_file(fpath)
        self.assertNot(os.path.exists(fpath))
        
    def test_remove_file_force(self):
        """ Test removing a read-only file forcefully. """
        dpath = self.__create_dir()
        fpath = os.path.join(dpath, "test")
        util.chmod(dpath, stat.S_IEXEC | stat.S_IREAD, recursive=True)
        util.remove_file(fpath, force=True)
        self.assertNot(os.path.exists(fpath))

    def test_remove_file_or_dir(self):
        dpath, fpath = self.__create_dir(), self._get_tempfname()
        util.remove_file_or_dir(dpath, recurse=True)
        util.remove_file_or_dir(fpath)
        self.assertNot(os.path.exists(dpath))
        self.assertNot(os.path.exists(fpath))

    def test_get_os(self):
        self.assertIn(srllib.util.get_os()[0], (srllib.util.Os_Linux,
                srllib.util.Os_Windows))

    def test_create_file_unicode(self):
        """ Test creating file with unicode content. """
        fpath = self._get_tempfname()
        util.create_file(fpath, content=u"æøå", encoding="utf-8")
        f = codecs.open(fpath, encoding="utf-8")
        try: self.assertEqual(f.read(), u"æøå")
        finally: f.close()
        
    def test_read_file_unicode(self):
        """ Test reading a file with unicode content. """
        fpath = self._get_tempfname()
        f = codecs.open(fpath, encoding="utf-8", mode="wb")
        try: f.write(u"Æøå")
        finally: f.close()
        self.assertEqual(util.read_file(fpath, encoding="utf-8"), u"Æøå")
        
    def test_create_file_bin(self):
        """ Test creating a file in binary mode. """
        f = util.create_file(self._get_tempfname(), binary=True, close=False)
        try:
            self.assertEqual(f.mode, "wb")
        finally: f.close()

    def test_create_file_invalid_encoding(self):
        """ Test creating a file with invalid encoding. """
        self.assertRaises(UnicodeDecodeError, util.create_file,
                self._get_tempfname(), content="æøå", encoding="ascii")
        
    def test_replace_root(self):
        fpath, newroot = self._get_tempfname(), self._get_tempdir()
        self.assertEqual(util.replace_root(fpath, newroot,
                os.path.dirname(fpath)), os.path.join(newroot,
                os.path.basename(fpath)))
        
    def test_replace_root_default(self):
        """ Test replace_root with default original root. """
        if util.get_os_name() in util.OsCollection_Posix:
            fpath, newroot = "/file", "/tmp/"
        elif util.get_os_name() == util.Os_Windows:
            fpath, newroot = r"C:\file", r"Z:\\"
        self.assertEqual(util.replace_root(fpath, newroot), os.path.join(
                newroot, "file"))
        
    def test_replace_root_noroot(self):
        """ Test calling replace_root with a name with no directory component.
        """
        self.assertEqual(util.replace_root("file", "some root"), "file")
        
    def test_resolve_path(self):
        """ Test resolving path to executable. """
        self.assertEquals(os.path.splitext(os.path.basename(
                util.resolve_path("python")))[0], "python")
        
    def test_resolve_path_notfound(self):
        """ Test resolving non-existent executable. """
        self.assertRaises(_srlerror.NotFound, util.resolve_path,
                "There is no such executable.")
        
    def test_compare_dirs(self):
        """ Test dir comparison. """
        dpath0 = self._get_tempdir()
        util.create_file(os.path.join(dpath0, "tmpfile"), "Test")
        self.assertEqual(util.compare_dirs(dpath0, dpath0, False), ([], []))
        
    def test_compare_dirs_missing(self):
        """ Test supplying missing directories to compare_dirs.
        """
        dpath = self._get_tempdir()
        self.assertRaises(ValueError, util.compare_dirs, "nosuchdir", dpath)
        self.assertRaises(ValueError, util.compare_dirs, dpath, "nosuchdir")
        
    def test_compare_dirs_first_empty(self):
        """ Test against an empty first directory. """
        dpath0, dpath1 = self._get_tempdir(), self._get_tempdir()
        util.create_file(os.path.join(dpath1, "file"))
        self.assertEqual(util.compare_dirs(dpath0, dpath1), ([], ["file"]))
        
    def test_compare_dirs_subdirs(self):
        """ Test compare_dirs with differing sub-directories. """
        dpath0, dpath1 = self._get_tempdir(), self._get_tempdir()
        subdir0, subdir1 = os.path.join(dpath0, "subdir"), os.path.join(dpath1,
                 "subdir")
        os.mkdir(subdir0)
        os.mkdir(subdir1)
        util.chmod(subdir0, 0)
        self.assertEqual(util.compare_dirs(dpath0, dpath1), (["subdir"], []))
        
    def test_clean_path(self):
        self.assertEqual(util.clean_path(os.path.join("dir", "..", "file")),
                os.path.join(os.path.abspath("file")))

    def __create_dir(self):
        """ Create directory with contents. """
        dpath = self._get_tempdir()
        # We put some content inside the created files, since read permissions
        # will not affect empty files (i.e., copying an empty file won't
        # provoke an error)
        util.create_file(os.path.join(dpath, "test"), "Test")
        os.mkdir(os.path.join(dpath, "testdir"))
        util.create_file(os.path.join(dpath, "testdir", "test"), "Test")
        return dpath
    
    def __create_tempfile(self, *args, **kwds):
        fpath = util.create_tempfile(*args, **kwds)
        self._tempfiles.append(fpath)
        return fpath

class VariousTest(TestCase):
    """ Test various functionality. """
    def test_get_checksum(self):
        dir0, dir1 = self._get_tempdir(), self._get_tempdir()
        self.assertEqual(util.get_checksum(dir0), util.get_checksum(dir1))
        fpath = util.create_file(os.path.join(dir1, "test"), "Test")
        chksum = util.get_checksum(dir1)
        self.assertNotEqual(util.get_checksum(dir0), chksum)
        self.assertEqual(util.get_checksum(fpath), chksum)
    
    def test_get_checksum_invalid_format(self):
        """ Pass invalid format to get_checksum. """
        self.assertRaises(ValueError, util.get_checksum, "somepath", -1)
        
    def test_get_checksum_bin(self):
        """ Test binary checksum (20 bytes). """
        self.assertEqual(len(util.get_checksum(self._get_tempfname(),
                util.Checksum_Binary)), 20)
    
    def test_get_module(self):
        """ Test the get_module function. """
        fpath = self._get_tempfname(content="test = True\n", suffix=".py")
        try: m = util.get_module(os.path.splitext(os.path.basename(fpath))[0],
                os.path.dirname(fpath))
        finally:
            # Remove .pyc
            os.remove(fpath + "c")
        self.assertEqual(m.test, True)
        
    def test_get_module_missing(self):
        """ Try finding a missing module. """
        dpath = self._get_tempdir()
        self.assertRaises(ValueError, util.get_module, "missing", dpath)
        
    def test_get_os_name(self):
        self.assertIn(util.get_os_name(), (util.Os_Windows, util.Os_Linux))
        
    def test_get_os_version(self):
        util.get_os_version()
        
    def test_get_os(self):
        self.assertEqual(util.get_os(), (util.get_os_name(),
                util.get_os_version()))
