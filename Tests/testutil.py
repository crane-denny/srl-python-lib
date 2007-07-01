""" Test the util module. """
import os.path, stat

from srllib.testing import *
from srllib import util

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

    def test_removedir(self):
        dpath = self.__createDir()
        self.assertRaises(util.DirNotEmpty, util.remove_dir, dpath, recurse=False)
        util.remove_dir(dpath, recurse=True)
        self.assertNot(os.path.exists(dpath))

        # Test removing an empty dir
        dpath = self._get_tempdir()
        util.remove_dir(dpath, recurse=False)
        self.assertNot(os.path.exists(dpath))

    def test_copydir(self):
        """ Test copying a directory.

        When a directory is copied, the client callback should be called periodically with
        progress status.
        """
        def callback(progress):
            self.__progress.append(progress)

        dpath = self.__createDir()
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
        dpath0, dpath1 = self.__createDir(), self._get_tempdir()
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
        fname = util.create_tempfile()
        try: self.assert_(isinstance(fname, basestring))
        finally: os.remove(fname)
        file_ = util.create_tempfile(close=False)
        try: self.assert_(isinstance(file_, file))
        finally:
            file_.close()
            os.remove(file_.name)
        file_ = util.create_tempfile(close=False, content="Test")
        try:
            self.assertEqual(file_.read(), "Test")
            file_.write("\nTest")
            file_.seek(0)
            self.assertEqual(file_.read(), "Test\nTest")
        finally: file_.close()

    def test_chmod(self):
        dpath = self.__createDir()
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

    def test_walkdir(self):
        entered = []
        root = self.__createDir()
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

    def test_remove_file_or_dir(self):
        dpath, fpath = self.__createDir(), self._get_tempfname()
        util.remove_file_or_dir(dpath, recurse=True)
        util.remove_file_or_dir(fpath)
        self.assertNot(os.path.exists(dpath))
        self.assertNot(os.path.exists(fpath))

    def test_get_module(self):
        file_ = self._get_tempfile(suffix=".py")
        try: file_.write("attr = 'value'\n")
        finally: file_.close()
        fpath = file_.name
        m = util.get_module(os.path.splitext(os.path.basename(fpath))[0], [os.path.dirname(fpath)])
        self.assertEqual(m.attr, "value")

        # Test a non-existing module
        self.assertRaises(ValueError, util.get_module, "nosuchmodule", [os.path.dirname(fpath)])

    def test_get_os(self):
        self.assertIn(srllib.util.get_os()[0], (srllib.util.Os_Linux,
                srllib.util.Os_Windows))

    def __createDir(self):
        dpath = self._get_tempdir()
        # We put some content inside the created files, since read permissions
        # will not affect empty files (i.e., copying an empty file won't
        # provoke an error)
        util.create_file(os.path.join(dpath, "test"), "Test")
        os.mkdir(os.path.join(dpath, "testdir"))
        util.create_file(os.path.join(dpath, "testdir", "test"), "Test")
        return dpath

class VariousTest(TestCase):
    """ Test various functionality. """
    def test_getchecksum(self):
        dir0, dir1 = self._get_tempdir(), self._get_tempdir()
        self.assertEqual(util.get_checksum(dir0), util.get_checksum(dir1))
        fpath = util.create_file(os.path.join(dir1, "test"), "Test")
        chksum = util.get_checksum(dir1)
        self.assertNotEqual(util.get_checksum(dir0), chksum)
        self.assertEqual(util.get_checksum(fpath), chksum)
