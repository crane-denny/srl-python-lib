""" Test the util module. """
import os.path, stat

from srllib.testing import *
from srllib import util

class FileSystemTest(TestCase):
    """ Test filesystem utility functions. """
    def testMoveFile(self):

        # There might be a problem moving a file onto another, we are testing this case as well
        # since the destination already exists
        dstDir = self._get_tempdir()
        src, dst = self._get_tempfile(), util.create_file(os.path.join(dstDir, "test"))
        try: src.write("Test")
        finally: src.close()

        util.chmod(dstDir, 0)
        self.assertRaises(util.PermissionsError, util.move_file, src.name, dst)
        util.chmod(dstDir, 0700)
        util.move_file(src.name, dst)
        f = file(dst)
        try: txt = f.read()
        finally: f.close()
        self.assertEqual(txt, "Test")
        self.assertNot(os.path.exists(src.name))

    def testRemoveDir(self):
        dpath = self.__createDir()
        self.assertRaises(util.DirNotEmpty, util.remove_dir, dpath, recurse=False)
        util.remove_dir(dpath, recurse=True)
        self.assertNot(os.path.exists(dpath))

        # Test removing an empty dir
        dpath = self._get_tempdir()
        util.remove_dir(dpath, recurse=False)
        self.assertNot(os.path.exists(dpath))

    def testCopyDir(self):
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
        util.chmod(dstDir, 0500)
        # Make sure we can access the directory (requires the correct permissions on dstDir)
        assert os.path.exists(os.path.join(dstDir, "testdir"))
        # This should fail, because the conflicting directory is protected from deletion
        self.assertRaises(util.PermissionsError, util.copy_dir, dpath, os.path.join(dstDir, "testdir"), force=True)
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

    def testCopyNoPerm(self):
        """ Test copying a directory with missing permissions. """
        dpath0, dpath1 = self.__createDir(), self._get_tempdir()
        util.chmod(dpath0, 0)
        self.assertRaises(util.PermissionsError, util.copy_dir, dpath0, dpath1, force=True)
        util.chmod(dpath0, 0700)
        # Test directory permissions
        util.chmod(os.path.join(dpath0, "testdir"), 0000)
        self.assertRaises(util.PermissionsError, util.copy_dir, dpath0, dpath1, force=True)
        # Test file permissions
        util.chmod(os.path.join(dpath0, "test"), 0700)
        util.chmod(os.path.join(dpath0, "test"), 0000)
        self.assertRaises(util.PermissionsError, util.copy_dir, dpath0, dpath1, force=True)

    def testCopyFile(self):
        src, dst = self._get_tempfile(), self._get_tempfname()
        try: src.write("Test")
        finally: src.close()
        util.copy_file(src.name, dst)
        f = file(dst)
        try: txt = f.read()
        finally: f.close()
        self.assertEqual(txt, "Test")

    def testCreateTemporaryFile(self):
        fname = util.create_tempfile()
        try:
            self.assert_(isinstance(fname, basestring))
        finally:
            os.remove(fname)
        file_ = util.create_tempfile(close=False)
        try: self.assert_(isinstance(file_, file))
        finally:
            file_.close()
            os.remove(file_.name)

    def testChmod(self):
        dpath = self.__createDir()
        util.chmod(dpath, 0)
        self.assertEqual(stat.S_IMODE(os.stat(dpath).st_mode), 0)
        self.assertRaises(util.PermissionsError, util.chmod, dpath, 0000, recursive=True)
        util.chmod(dpath, 0700)
        util.chmod(dpath, 0000, recursive=True)
        util.chmod(dpath, 0700)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(dpath, "test")).st_mode), 0)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(dpath, "testdir")).st_mode), 0)

    def testWalkDir(self):
        entered = []
        root = self.__createDir()
        for dpath, dnames, fnames in util.walkdir(root):
            entered.append(dpath)
        self.assertEqual(entered, [root, os.path.join(root, "testdir")])

    def testRemove_file(self):
        dpath = self._get_tempdir()
        fpath = util.create_file(os.path.join(dpath, "test"))
        util.chmod(dpath, 0)
        self.assertRaises(util.PermissionsError, util.remove_file, fpath)
        util.chmod(dpath, 0700)
        util.remove_file(fpath)
        self.assertNot(os.path.exists(fpath))

    def testRemove_file_or_dir(self):
        dpath, fpath = self.__createDir(), self._get_tempfname()
        util.remove_file_or_dir(dpath, recurse=True)
        util.remove_file_or_dir(fpath)
        self.assertNot(os.path.exists(dpath))
        self.assertNot(os.path.exists(fpath))

    def testGetModule(self):
        file_ = self._get_tempfile(suffix=".py")
        try: file_.write("attr = 'value'\n")
        finally: file_.close()
        fpath = file_.name
        m = util.get_module(os.path.splitext(os.path.basename(fpath))[0], [os.path.dirname(fpath)])
        self.assertEqual(m.attr, "value")

        # Test a non-existing module
        self.assertRaises(ValueError, util.get_module, "nosuchmodule", [os.path.dirname(fpath)])

    def test_get_os(self):
        self.assertIn(srllib.util.get_os()[0], srllib.util.Os_Linux,
                srllib.util.Os_Windows)

    def __createDir(self):
        dpath = self._get_tempdir()
        file(os.path.join(dpath, "test"), "w")
        os.mkdir(os.path.join(dpath, "testdir"))
        file(os.path.join(dpath, "testdir", "test"), "w")
        return dpath

class VariousTest(TestCase):
    """ Test various functionality. """
    def testGetChecksum(self):
        dir0, dir1 = self._get_tempdir(), self._get_tempdir()
        self.assertEqual(util.get_checksum(dir0), util.get_checksum(dir1))
        fpath = util.create_file(os.path.join(dir1, "test"), "Test")
        chksum = util.get_checksum(dir1)
        self.assertNotEqual(util.get_checksum(dir0), chksum)
        self.assertEqual(util.get_checksum(fpath), chksum)
