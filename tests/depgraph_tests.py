import unittest
import sys
import os
import shutil
import time

import depgraph
from depgraph import Dataset, DatasetGroup, DependencyGraph

TESTDIR = os.path.abspath(os.getcwd())

def makefile(fnm, content=None):
    if content is None:
        content = fnm
    with open(fnm, "w") as f:
        f.write(content)
    return

def ensureisdir(dirname):
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    return

def cleandir(dirname):
    for fnm in os.listdir(dirname):
        os.remove(os.path.join(dirname, fnm))
    return

def fullpath(p):
    return os.path.join(TESTDIR, p)

class SetterUpper(object):

    def setUp(self):
        """ define a simple dependency graph that is complex enough to be
        interesting.
        
         R0      R1      R2      R3         [raw data]
           \     /       |       |
             DA0         DA1    /
                 \      /  \   /
                    DB0     DB1
                     \     / |  \
                      \   /  |   \
                       DC0  DC1  DC2        [products]
        """
        raw0 = Dataset(fullpath("testdata/raw0"), prog="rawdata")
        raw1 = Dataset(fullpath("testdata/raw1"), prog="rawdata")
        raw2 = Dataset(fullpath("testdata/raw2"), prog="rawdata")
        raw3 = Dataset(fullpath("testdata/raw3"), prog="rawdata")
        
        da0 = Dataset(fullpath("testproject/da0"), prog="step1")
        da1 = Dataset(fullpath("testproject/da1"), prog="step2")

        db0 = Dataset(fullpath("testproject/db0"), prog="step3")
        db1 = Dataset(fullpath("testproject/db1"), prog="step4")

        dc0 = Dataset(fullpath("testproject/dc0"), prog="step5")
        dc1 = Dataset(fullpath("testproject/dc1"), prog="step6")
        dc2 = Dataset(fullpath("testproject/dc2"), prog="step7")

        DC = DependencyGraph()

        DC.add_dataset(da0, (raw0, raw1))
        DC.add_dataset(da1, (raw2,))
        DC.add_dataset(db0, (da0, da1))
        DC.add_dataset(db1, (da1, raw3))
        DC.add_dataset(dc0, (db0, db1))
        DC.add_dataset(dc1, (db1,))
        DC.add_dataset(dc2, (db1,))

        self.da0 = da0
        self.da1 = da1
        self.db0 = db0
        self.db1 = db1
        self.dc0 = dc0
        self.dc1 = dc1
        self.dc2 = dc2

        self.dc = DC

        # initialize "raw" data
        rawdir = fullpath("testdata")
        ensureisdir(rawdir)

        for dep in (raw0, raw1, raw2, raw3):
            makefile(dep.name)
        time.sleep(0.05)
        return

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(fullpath("testdata")):
            os.makedirs(fullpath("testdata"))
        if not os.path.isdir(fullpath("testproject")):
            os.makedirs(fullpath("testproject"))
        return


class NeedsBuildTests(SetterUpper, unittest.TestCase):

    # @classmethod
    # def tearDownClass(cls):
    #     shutil.rmtree(fullpath("testdata"))
    #     shutil.rmtree(fullpath("testproject"))
    #     return

    def test_linear_build_all(self):
        """ this tests the straightforward case, where none of the files exist,
        and must be build from the beginning.
        """
        # create the file hierarchy
        # (no files exist)
        cleandir(fullpath("testproject"))

        # build dc0
        steps = []
        for dep, _ in self.dc.needsbuild(self.dc0):
            steps.append(dep.name)

        self.assertTrue(steps.index(fullpath("testproject/da0")) <
                        steps.index(fullpath("testproject/db0")))
        self.assertTrue(steps.index(fullpath("testproject/da1")) <
                        steps.index(fullpath("testproject/db0")))
        self.assertTrue(steps.index(fullpath("testproject/da1")) <
                        steps.index(fullpath("testproject/db1")))
        self.assertTrue(steps.index(fullpath("testproject/dc0")) >
                        steps.index(fullpath("testproject/db0")))
        self.assertTrue(steps.index(fullpath("testproject/dc0")) >
                        steps.index(fullpath("testproject/db1")))

        # build dc1
        steps = []
        reasons = []
        for dep, reason in self.dc.needsbuild(self.dc1):
            steps.append(dep.name)
            reasons.append(reason)

        for reason in reasons[:-1]:
            self.assertEqual(str(reason), "the target is descended from it")

        self.assertTrue(steps.index(fullpath("testproject/da1")) <
                        steps.index(fullpath("testproject/db1")))
        self.assertTrue(steps.index(fullpath("testproject/db1")) <
                        steps.index(fullpath("testproject/dc1")))
        return

    def test_has_intermediate_files(self):
        """ test the case where intermediate files exist that can be used to speed the build
        """
        # create the file hierarchy
        ensureisdir(fullpath("testproject"))
        cleandir(fullpath("testproject"))
        makefile(self.da0.name)
        makefile(self.da1.name)
        makefile(self.db1.name)

        # build dc0
        steps = []
        for dep, _ in self.dc.needsbuild(self.dc0):
            steps.append(dep.name)

        self.assertEqual(steps, [fullpath("testproject/db0"),
                                 fullpath("testproject/dc0")])

        # build dc1
        steps = []
        for dep, _ in self.dc.needsbuild(self.dc1):
            steps.append(dep.name)

        self.assertEqual(steps, [fullpath("testproject/dc1")])
        return

    def test_has_intermediate_files_needs_rebuild(self):
        """ test the case where intermediate files exist, but they're out of
        date and require rebuilding
        """
        # create the file hierarchy
        ensureisdir(fullpath("testproject"))
        cleandir(fullpath("testproject"))
        makefile(self.db0.name)
        makefile(self.db1.name)
        time.sleep(0.05)
        makefile(self.da0.name)
        makefile(self.da1.name)

        # build dc0
        steps = []
        reasons = []
        for dep, reason in self.dc.needsbuild(self.dc0):
            steps.append(dep.name)
            reasons.append(reason)

        self.assertEqual(len(steps), 3)
        self.assertEqual(str(reasons[0]), "it is older than at least one of its parents")
        self.assertEqual(str(reasons[1]), "it is older than at least one of its parents")
        self.assertEqual(str(reasons[2]), "it is the target")
        self.assertTrue(steps.index(fullpath("testproject/db0")) <
                        steps.index(fullpath("testproject/dc0")))
        self.assertTrue(steps.index(fullpath("testproject/db1")) <
                        steps.index(fullpath("testproject/dc0")))

        # build dc1
        steps = []
        for dep, _ in self.dc.needsbuild(self.dc1):
            steps.append(dep.name)

        self.assertEqual(len(steps), 2)
        self.assertTrue(steps.index(fullpath("testproject/db1")) <
                        steps.index(fullpath("testproject/dc1")))
        return

    def test_missing_graph_root(self):
        cleandir(fullpath("testdata/"))
        with self.assertRaises(RuntimeError):
            list(self.dc.needsbuild(self.dc0))
        return

class BuildableTests(SetterUpper, unittest.TestCase):

    def test_buildable_one_level(self):
        # mostly just checks that it doesn't fail
        cleandir(fullpath("testproject"))
        tobuild = list(self.dc.buildable(self.db0))
        self.assertTrue(self.da0 in tobuild)
        self.assertTrue(self.da1 in tobuild)
        self.assertEqual(len(tobuild), 2)
        return

    def test_buildable_two_level(self):
        cleandir(fullpath("testproject"))
        tobuild = list(self.dc.buildable(self.dc0))

        self.assertTrue(self.da0 in tobuild)
        self.assertTrue(self.da1 in tobuild)
        self.assertTrue(self.db1 in tobuild)
        self.assertEqual(len(tobuild), 3)

        for ds in tobuild:
            makefile(ds.name)

        tobuild2 = list(self.dc.buildable(self.dc0))

        self.assertTrue(self.db0 in tobuild2)
        self.assertEqual(len(tobuild2), 1)
        return

class SimpleDependencyGraphTests(unittest.TestCase):

    def setUp(self):
        """
            R0  R1  R2
             \ /    |
             I0     I1
               \   /
               FINAL
        """
        dc = DependencyGraph()
        dc.add_dataset("final_result", ["intermediate0", "intermediate1", "raw0"])
        dc.add_relation("intermediate0", "raw0")
        dc.add_relation("intermediate0", "raw1")
        dc.add_relation("intermediate1", "raw2")
        self.dc = dc

    def test_buildsteps(self):
        # this test has problems
        steps = self.dc.buildsteps("final_result")

        self.assertTrue(steps.index("raw2") < steps.index("intermediate1"))
        self.assertTrue(steps.index("raw0") < steps.index("intermediate0"))
        self.assertTrue(steps.index("raw1") < steps.index("intermediate0"))
        self.assertTrue(steps.index("final_result") > steps.index("intermediate0"))
        self.assertTrue(steps.index("final_result") > steps.index("intermediate1"))
        return

    def test_dependson1(self):
        self.assertEqual(self.dc.dependson("raw1"),
                         set(["intermediate0", "final_result"]))
        return

    def test_dependson2(self):
        self.assertEqual(self.dc.dependson("raw1", depth=0),
                         set(["intermediate0"]))
        return

    def test_leadsto1(self):
        self.assertEqual(self.dc.leadsto("intermediate0"),
                         set(["raw0", "raw1"]))
        return

    def test_leadsto2(self):
        self.assertEqual(self.dc.leadsto("final_result"),
                         set(["raw0", "raw1", "raw2", "intermediate0", "intermediate1"]))
        return

    def test_getroots(self):
        roots = self.dc.getroots("final_result")
        self.assertEqual(roots, set(["raw0", "raw1", "raw2"]))

class DatasetGroupTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(fullpath("testdata")):
            os.makedirs(fullpath("testdata"))
        return

    # @classmethod
    # def tearDownClass(cls):
    #     shutil.rmtree(fullpath("testdata"))
    #     return


    def test_isolder1(self):
        """ define two dependency groups, where all files are older in one
        than in the other. """
        dep1a = Dataset(fullpath("testdata/1a"))
        dep1b = Dataset(fullpath("testdata/1b"))
        dep1c = Dataset(fullpath("testdata/1c"))

        for dep in (dep1a, dep1b, dep1c):
            makefile(dep.name)
        time.sleep(0.05)

        dep2a = Dataset(fullpath("testdata/2a"))
        dep2b = Dataset(fullpath("testdata/2b"))
        dep2c = Dataset(fullpath("testdata/2c"))

        for dep in (dep2a, dep2b, dep2c):
            makefile(dep.name)

        group1 = DatasetGroup(fullpath("testdata/1"), [dep1a, dep1b, dep1c])
        group2 = DatasetGroup(fullpath("testdata/2"), [dep2a, dep2b, dep2c])

        self.assertTrue(depgraph.isolder(group1, group2))

    def test_isolder2(self):
        """ define two dependency groups, where files ages overlap, and so
        group 1 is not absolutely older than group 2 """
        dep1a = Dataset(fullpath("testdata/1a"))
        dep1b = Dataset(fullpath("testdata/1b"))
        dep2c = Dataset(fullpath("testdata/2c"))

        for dep in (dep1a, dep1b, dep2c):
            makefile(dep.name)
        time.sleep(0.05)

        dep1c = Dataset(fullpath("testdata/1c"))
        dep2a = Dataset(fullpath("testdata/2a"))
        dep2b = Dataset(fullpath("testdata/2b"))

        for dep in (dep1c, dep2a, dep2b):
            makefile(dep.name)

        group1 = DatasetGroup(fullpath("testdata/1"), [dep1a, dep1b, dep1c])
        group2 = DatasetGroup(fullpath("testdata/2"), [dep2a, dep2b, dep2c])

        self.assertFalse(depgraph.isolder(group1, group2))

    def test_isolder3(self):
        """ compare a dependency group to a singular dependency """
        dep1a = Dataset(fullpath("testdata/1a"))
        dep1b = Dataset(fullpath("testdata/1b"))
        dep1c = Dataset(fullpath("testdata/1c"))

        group1 = DatasetGroup(fullpath("testdata/1"), [dep1a, dep1b, dep1c])

        for dep in group1:
            makefile(dep.name)
        time.sleep(0.05)

        dep2 = Dataset(fullpath("testdata/2"))
        makefile(dep2.name)

        self.assertTrue(depgraph.isolder(group1, dep2))

if __name__ == "__main__":
    unittest.main()
