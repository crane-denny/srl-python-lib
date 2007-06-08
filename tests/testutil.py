""" Test the util module. """
import os.path, stat

from simula.testing import *
from simula import util

class FileSystemTest(TestCase):
    """ Test filesystem utility functions. """
    def testMoveFile(self):

        # There might be a problem moving a file onto another, we are testing this case as well
        # since the destination already exists
        dstDir = self._getTempDir()
        src, dst = self._getTempFile(), util.createFile(os.path.join(dstDir, "test"))
        try: src.write("Test")
        finally: src.close()

        util.chmod(dstDir, 0)
        self.assertRaises(util.PermissionsError, util.moveFile, src.name, dst)
        util.chmod(dstDir, 0700)
        util.moveFile(src.name, dst)
        f = file(dst)
        try: txt = f.read()
        finally: f.close()
        self.assertEqual(txt, "Test")
        self.assertNot(os.path.exists(src.name))

    def testRemoveDir(self):
        dpath = self.__createDir()
        self.assertRaises(util.DirNotEmpty, util.removeDir, dpath, recurse=False)
        util.removeDir(dpath, recurse=True)
        self.assertNot(os.path.exists(dpath))

        # Test removing an empty dir
        dpath = self._getTempDir()
        util.removeDir(dpath, recurse=False)
        self.assertNot(os.path.exists(dpath))

    def testCopyDir(self):
        """ Test copying a directory.

        When a directory is copied, the client callback should be called periodically with
        progress status.
        """
        def callback(progress):
            self.__progress.append(progress)

        dpath = self.__createDir()
        dstDir = self._getTempDir()
        self.assertRaises(util.DestinationExists, util.copyDir, dpath, dstDir)

        # Try forcing deletion of existing directory

        os.mkdir(os.path.join(dstDir, "testdir"))
        # Remove only write permission
        util.chmod(dstDir, 0500)
        # Make sure we can access the directory (requires the correct permissions on dstDir)
        assert os.path.exists(os.path.join(dstDir, "testdir"))
        # This should fail, because the conflicting directory is protected from deletion
        self.assertRaises(util.PermissionsError, util.copyDir, dpath, os.path.join(dstDir, "testdir"), force=True)
        util.chmod(dstDir, 0700)
        util.copyDir(dpath, dstDir, force=True)

        util.removeDir(dstDir, recurse=True)
        self.__progress = []
        util.copyDir(dpath, dstDir, callback=callback)
        self.assertEqual(compareDirs(dpath, dstDir), ([], []))
        self.assertEqual(self.__progress[0], 0.0)
        self.assertEqual(self.__progress[-1], 100.0)

        # Test ignoring certain files
        dpath = self._getTempDir()
        os.mkdir(os.path.join(dpath, ".svn"))
        util.createFile(os.path.join(dpath, "test"))
        dstDir = self._getTempDir()
        util.copyDir(dpath, dstDir, ignore=[".*"], force=True)
        self.assertEqual(os.listdir(dstDir), ["test"])

    def testCopyNoPerm(self):
        """ Test copying a directory with missing permissions. """
        dpath0, dpath1 = self.__createDir(), self._getTempDir()
        util.chmod(dpath0, 0)
        self.assertRaises(util.PermissionsError, util.copyDir, dpath0, dpath1, force=True)
        util.chmod(dpath0, 0700)
        # Test directory permissions
        util.chmod(os.path.join(dpath0, "testdir"), 0000)
        self.assertRaises(util.PermissionsError, util.copyDir, dpath0, dpath1, force=True)
        # Test file permissions
        util.chmod(os.path.join(dpath0, "test"), 0700)
        util.chmod(os.path.join(dpath0, "test"), 0000)
        self.assertRaises(util.PermissionsError, util.copyDir, dpath0, dpath1, force=True)

    def testCopyFile(self):
        src, dst = self._getTempFile(), self._getTempFname()
        try: src.write("Test")
        finally: src.close()
        util.copyFile(src.name, dst)
        f = file(dst)
        try: txt = f.read()
        finally: f.close()
        self.assertEqual(txt, "Test")

    def testCreateTemporaryFile(self):
        fname = util.createTemporaryFile()
        try:
            self.assert_(isinstance(fname, basestring))
        finally:
            os.remove(fname)
        file_ = util.createTemporaryFile(close=False)
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
        for dpath, dnames, fnames in util.walkDir(root):
            entered.append(dpath)
        self.assertEqual(entered, [root, os.path.join(root, "testdir")])

    def testRemoveFile(self):
        dpath = self._getTempDir()
        fpath = util.createFile(os.path.join(dpath, "test"))
        util.chmod(dpath, 0)
        self.assertRaises(util.PermissionsError, util.removeFile, fpath)
        util.chmod(dpath, 0700)
        util.removeFile(fpath)
        self.assertNot(os.path.exists(fpath))

    def testRemoveFileOrDir(self):
        dpath, fpath = self.__createDir(), self._getTempFname()
        util.removeFileOrDir(dpath, recurse=True)
        util.removeFileOrDir(fpath)
        self.assertNot(os.path.exists(dpath))
        self.assertNot(os.path.exists(fpath))

    def testGetModule(self):
        file_ = self._getTempFile(suffix=".py")
        try: file_.write("attr = 'value'\n")
        finally: file_.close()
        fpath = file_.name
        m = util.getModule(os.path.splitext(os.path.basename(fpath))[0], [os.path.dirname(fpath)])
        self.assertEqual(m.attr, "value")

        # Test a non-existing module
        self.assertRaises(ValueError, util.getModule, "nosuchmodule", [os.path.dirname(fpath)])

    def __createDir(self):
        dpath = self._getTempDir()
        file(os.path.join(dpath, "test"), "w")
        os.mkdir(os.path.join(dpath, "testdir"))
        file(os.path.join(dpath, "testdir", "test"), "w")
        return dpath

class VariousTest(TestCase):
    """ Test various functionality. """
    def testGetChecksum(self):
        dir0, dir1 = self._getTempDir(), self._getTempDir()
        self.assertEqual(util.getChecksum(dir0), util.getChecksum(dir1))
        fpath = util.createFile(os.path.join(dir1, "test"), "Test")
        chksum = util.getChecksum(dir1)
        self.assertNotEqual(util.getChecksum(dir0), chksum)
        self.assertEqual(util.getChecksum(fpath), chksum)
