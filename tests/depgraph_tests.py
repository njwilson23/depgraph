import unittest
import sys
import os
import time

import depgraph
from depgraph import Dependency, DependencyGraph

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

class NeedsBuildTests(unittest.TestCase):

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
        raw0 = Dependency("testdata/raw0", prog="rawdata")
        raw1 = Dependency("testdata/raw1", prog="rawdata")
        raw2 = Dependency("testdata/raw2", prog="rawdata")
        raw3 = Dependency("testdata/raw3", prog="rawdata")
        
        da0 = Dependency("testproject/da0", prog="step1")
        da1 = Dependency("testproject/da1", prog="step2")

        db0 = Dependency("testproject/db0", prog="step3")
        db1 = Dependency("testproject/db1", prog="step4")

        dc0 = Dependency("testproject/dc0", prog="step5")
        dc1 = Dependency("testproject/dc1", prog="step6")
        dc2 = Dependency("testproject/dc2", prog="step7")

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
        rawdir = os.path.join(TESTDIR, "testdata")
        ensureisdir(rawdir)

        for dep in (raw0, raw1, raw2, raw3):
            makefile(dep.name)
        time.sleep(0.05)
        return

    def test_linear_build_all(self):
        """ this tests the straightforward case, where none of the files exist,
        and must be build from the beginning.
        """
        # create the file hierarchy
        # (no files exist)
        cleandir(os.path.join(TESTDIR, "testproject"))

        # build dc0
        steps = []
        for dep, _ in self.dc.needsbuild(self.dc0):
            steps.append(dep.name)

        self.assertTrue(steps.index("testproject/da0") < steps.index("testproject/db0"))
        self.assertTrue(steps.index("testproject/da1") < steps.index("testproject/db0"))
        self.assertTrue(steps.index("testproject/da1") < steps.index("testproject/db1"))
        self.assertTrue(steps.index("testproject/dc0") > steps.index("testproject/db0"))
        self.assertTrue(steps.index("testproject/dc0") > steps.index("testproject/db1"))

        # build dc1
        steps = []
        reasons = []
        for dep, reason in self.dc.needsbuild(self.dc1):
            steps.append(dep.name)
            reasons.append(reason)

        for reason in reasons[:-1]:
            self.assertEqual(str(reason), "the target is descended from it")

        self.assertTrue(steps.index("testproject/da1") < steps.index("testproject/db1"))
        self.assertTrue(steps.index("testproject/db1") < steps.index("testproject/dc1"))
        return

    def test_has_intermediate_files(self):
        """ test the case where intermediate files exist that can be used to speed the build
        """
        # create the file hierarchy
        ensureisdir(os.path.join(TESTDIR, "testproject"))
        cleandir(os.path.join(TESTDIR, "testproject"))
        makefile(self.da0.name)
        makefile(self.da1.name)
        makefile(self.db1.name)

        # build dc0
        steps = []
        for dep, _ in self.dc.needsbuild(self.dc0):
            steps.append(dep.name)

        self.assertEqual(steps, ["testproject/db0", "testproject/dc0"])

        # build dc1
        steps = []
        for dep, _ in self.dc.needsbuild(self.dc1):
            steps.append(dep.name)

        self.assertEqual(steps, ["testproject/dc1"])
        return

    def test_has_intermediate_files_needs_rebuild(self):
        """ test the case where intermediate files exist, but they're out of
        date and require rebuilding
        """
        # create the file hierarchy
        ensureisdir(os.path.join(TESTDIR, "testproject"))
        cleandir(os.path.join(TESTDIR, "testproject"))
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
        self.assertTrue(steps.index("testproject/db0") < steps.index("testproject/dc0"))
        self.assertTrue(steps.index("testproject/db1") < steps.index("testproject/dc0"))

        # build dc1
        steps = []
        for dep, _ in self.dc.needsbuild(self.dc1):
            steps.append(dep.name)

        self.assertEqual(len(steps), 2)
        self.assertTrue(steps.index("testproject/db1") < steps.index("testproject/dc1"))
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


if __name__ == "__main__":
    unittest.main()
