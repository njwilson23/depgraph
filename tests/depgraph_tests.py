import os
import sys
import time
import unittest

import depgraph
from depgraph import Dataset, DatasetGroup, buildmanager

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

        da0.dependson(raw0, raw1)
        da1.dependson(raw2)
        db0.dependson(da0, da1)
        db1.dependson(da1, raw3)
        dc0.dependson(db0, db1)
        dc1.dependson(db1)
        dc2.dependson(db1)

        self.raw0 = raw0
        self.raw1 = raw1
        self.raw2 = raw2
        self.raw3 = raw3
        self.da0 = da0
        self.da1 = da1
        self.db0 = db0
        self.db1 = db1
        self.dc0 = dc0
        self.dc1 = dc1
        self.dc2 = dc2

        # initialize "raw" data
        rawdir = fullpath("testdata")
        ensureisdir(rawdir)

        for dep in (raw0, raw1, raw2, raw3):
            makefile(dep.name)
        time.sleep(0.05)
        cleandir(fullpath("testproject"))
        return

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(fullpath("testdata")):
            os.makedirs(fullpath("testdata"))
        if not os.path.isdir(fullpath("testproject")):
            os.makedirs(fullpath("testproject"))
        return

class BuildnextTests(SetterUpper, unittest.TestCase):

    def test_buildnext_one_level(self):
        tobuild = [dep for dep, reason in self.db0.buildnext()]
        self.assertTrue(self.da0 in tobuild)
        self.assertTrue(self.da1 in tobuild)
        self.assertEqual(len(tobuild), 2)
        return

    def test_buildnext_one_level_ignore(self):
        tobuild = [dep for dep, reason in self.db0.buildnext(ignore=[self.da1])]
        self.assertTrue(self.da0 in tobuild)
        self.assertTrue(self.da1 not in tobuild)
        self.assertEqual(len(tobuild), 1)
        return

    def test_buildnext_two_level(self):
        tobuild = [dep for dep, reason in self.dc0.buildnext()]

        self.assertTrue(self.da0 in tobuild)
        self.assertTrue(self.da1 in tobuild)
        self.assertEqual(len(tobuild), 2)

        for ds in tobuild:
            makefile(ds.name)

        tobuild2 = [dep for dep, reason in self.dc0.buildnext()]

        self.assertTrue(self.db1 in tobuild2)
        self.assertTrue(self.db0 in tobuild2)
        self.assertEqual(len(tobuild2), 2)
        return

class BuildManagerTests(SetterUpper, unittest.TestCase):

    def test_buildmanager_unecessary(self):
        # This should be a no-op, because target and all dependencies already
        # exist and the target is younger that any dependency. If the build
        # function is called, fail the test.

        @buildmanager
        def build(dep, reason):
            self.fail("unecessary build requested")
            return 0

        makefile(self.raw2.name)
        makefile(self.raw3.name)
        makefile(self.da1.name)
        makefile(self.db1.name)
        build(self.db1)
        return

    def test_perfect_builder(self):
        """ build manager from a delegator function that always succeeds """

        @buildmanager
        def build(dep, reason):
            makefile(dep.name)
            return 0

        out = build(self.dc0)

        self.assertTrue(os.path.isfile(self.da0.name))
        self.assertTrue(os.path.isfile(self.da1.name))
        self.assertTrue(os.path.isfile(self.db0.name))
        self.assertTrue(os.path.isfile(self.db1.name))
        return

    def test_perfect_builder_zero_attempt(self):
        """ build manager from a delegator function that always succeeds """

        @buildmanager
        def build(dep, reason):
            makefile(dep.name)
            return 0

        out = build(self.dc0, max_attempts=0)

        self.assertFalse(os.path.isfile(self.da0.name))
        self.assertFalse(os.path.isfile(self.da1.name))
        self.assertFalse(os.path.isfile(self.db0.name))
        self.assertFalse(os.path.isfile(self.db1.name))
        return

    @unittest.skipIf(sys.version_info < (3, 2), "requires concurrent.futures")
    def test_parallel_builder(self):

        import concurrent.futures

        def build(dep, reason):
            makefile(dep.name)
            return reason

        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            for stage in depgraph.buildall(self.dc0):
                for dep, reason in stage:
                    futures.append(pool.submit(build, dep, reason))
        concurrent.futures.wait(futures)

        self.assertTrue(os.path.isfile(self.da0.name))
        self.assertTrue(os.path.isfile(self.da1.name))
        self.assertTrue(os.path.isfile(self.db0.name))
        self.assertTrue(os.path.isfile(self.db1.name))
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
        result = Dataset("final_result")
        intermediate0 = Dataset("intermediate0")
        intermediate1 = Dataset("intermediate1")
        raw0 = Dataset("raw0")
        raw1 = Dataset("raw1")
        raw2 = Dataset("raw2")

        result.dependson(intermediate0, intermediate1, raw0)
        intermediate0.dependson(raw0, raw1)
        intermediate1.dependson(raw2)

        self.result = result
        self.intermediate0 = intermediate0
        self.intermediate1 = intermediate1
        self.raw0 = raw0
        self.raw1 = raw1
        self.raw2 = raw2
        return

    def test_dependson1(self):
        self.assertEqual(set(self.raw1.children()),
                         set([self.intermediate0, self.result]))
        return

    def test_dependson2(self):
        self.assertEqual(set(self.raw1.children(0)), set([self.intermediate0]))
        return

    def test_leadsto1(self):
        self.assertEqual(set(self.intermediate0.parents()),
                         set([self.raw0, self.raw1]))
        return

    def test_leadsto2(self):
        self.assertEqual(set(self.result.parents()),
                         set([self.raw0, self.raw1, self.raw2,
                              self.intermediate0, self.intermediate1]))
        return

    def test_getroots(self):
        roots = self.result.roots()
        self.assertEqual(set(roots), set([self.raw0, self.raw1, self.raw2]))

class DatasetGroupTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(fullpath("testdata")):
            os.makedirs(fullpath("testdata"))
        return

    def test_is_older1(self):
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

        self.assertTrue(group1.is_older_than(group2))

    def test_is_older2(self):
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

        self.assertFalse(group1.is_older_than(group2))

    def test_is_older3(self):
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

        self.assertTrue(group1.is_older_than(dep2))

    def test_parents(self):

        d1a = Dataset("1a")
        d1b = Dataset("1b")
        d1c = Dataset("1c")
        d1d = Dataset("1d")

        d2a = Dataset("2a")
        d2b = Dataset("2b")
        d2c = Dataset("2c")

        d2a.dependson(d1a, d1b)
        d2b.dependson(d1c)
        d2c.dependson(d1d)

        dg = DatasetGroup("dg", [d2a, d2b, d2c])
        self.assertEqual(set(dg.parents()), set([d1a, d1b, d1c, d1d]))

    def test_children(self):

        d1a = Dataset("1a")
        d1b = Dataset("1b")
        d1c = Dataset("1c")
        d1d = Dataset("1d")

        d2a = Dataset("2a")
        d2b = Dataset("2b")
        d2c = Dataset("2c")

        d2a.dependson(d1a, d1b)
        d2b.dependson(d1c)
        d2c.dependson(d1d)

        dg = DatasetGroup("dg", [d1a, d1b, d1c])
        self.assertEqual(set(dg.children()), set([d2a, d2b]))


class BuildallTests(SetterUpper, unittest.TestCase):

    def test_buildall(self):

        for i, group in enumerate(depgraph.buildall(self.dc0)):
            datasets = [d for d,_ in group]
            if i == 0:
                self.assertTrue(self.da0 in datasets)
                self.assertTrue(self.da1 in datasets)
            elif i == 1:
                self.assertTrue(self.db0 in datasets)
                self.assertTrue(self.db1 in datasets)
            elif i == 2:
                self.assertTrue(self.dc0 in datasets)
            else:
                raise ValueError

    def test_buildall_partial(self):

        # R0      R1      R2      R3         [raw data]
        #   \     /       |       |
        #    [DA0]        DA1    /
        #         \      /  \   /
        #            DB0     DB1
        #             \     / |  \
        #              \   /  |   \
        #               DC0  DC1  DC2        [products]

        makefile(self.da1.name)
        makefile(self.db0.name)
        makefile(self.db1.name)
        makefile(self.dc0.name)
        makefile(self.dc1.name)
        makefile(self.dc2.name)

        stage_count = 0
        for i, group in enumerate(depgraph.buildall(self.dc0)):
            stage_count += 1
            datasets = set([d for d,_ in group])
            if i == 0:
                self.assertEqual(datasets, set([self.da0]))
            elif i == 1:
                self.assertEqual(datasets, set([self.db0]))
            elif i == 2:
                self.assertEqual(datasets, set([self.dc0]))
            else:
                raise ValueError
        self.assertEqual(stage_count, 3)

class CyclicGraphDetectionTests(unittest.TestCase):

    def test_acyclic1(self):
        a = Dataset("a")
        b = Dataset("b")
        c = Dataset("c")
        d = Dataset("d")
        e = Dataset("e")
        f = Dataset("f")
        f.dependson(d, e)
        e.dependson(b, c)
        d.dependson(b)
        c.dependson(a)
        b.dependson(a)
        self.assertTrue(depgraph.is_acyclic(f))

    def test_acyclic2(self):
        a = Dataset("a")
        b = Dataset("b")
        c = Dataset("c")
        d = Dataset("d")
        e = Dataset("e")
        f = Dataset("f")
        f.dependson(d, e)
        e.dependson(b, c)
        d.dependson(b)
        c.dependson(a, d)
        b.dependson(a)
        self.assertTrue(depgraph.is_acyclic(f))

    def test_cyclic1(self):
        a = Dataset("a")
        b = Dataset("b")
        c = Dataset("c")
        d = Dataset("d")
        e = Dataset("e")
        f = Dataset("f")
        f.dependson(d, e)
        e.dependson(b, c)
        d.dependson(b)
        c.dependson(a, f)
        b.dependson(a)
        self.assertFalse(depgraph.is_acyclic(f))

    def test_cyclic2(self):
        a = Dataset("a")
        b = Dataset("b")
        c = Dataset("c")
        d = Dataset("d")
        e = Dataset("e")
        f = Dataset("f")
        a.dependson(f)
        f.dependson(d, e)
        e.dependson(b, c)
        d.dependson(b)
        c.dependson(a)
        b.dependson(a)
        self.assertFalse(depgraph.is_acyclic(f))

class GraphvizTests(unittest.TestCase):

    def test_graph(self):
        a = Dataset("a")
        b = Dataset("b")
        c = Dataset("c")
        d = Dataset("d")
        d.dependson(c)
        c.dependson(a, b)

        dot = depgraph.graphviz(d)
        self.assertEqual(len(dot.split("\n")), 5)
        self.assertTrue('"c" -> "d"' in dot)
        self.assertTrue('"a" -> "c"' in dot)
        self.assertTrue('"b" -> "c"' in dot)

    def test_graph_include(self):
        a = Dataset("a")
        b = Dataset("b")
        c = Dataset("c")
        d = Dataset("d")
        d.dependson(c)
        c.dependson(a, b)

        # Include only parents of `d`
        dot = depgraph.graphviz(d, include=lambda d1, d2: d in d1.children(0))
        self.assertEqual(len(dot.split("\n")), 3)
        self.assertTrue('"c" -> "d"' in dot)

    def test_graph_edge_style(self):
        a = Dataset("violet")
        b = Dataset("green")
        c = Dataset("red")
        d = Dataset("blue")
        d.dependson(c)
        c.dependson(a, b)

        dot = depgraph.graphviz(d, style=lambda d1, d2: {"color": d2.name, "weight": 2})
        self.assertEqual(len(dot.split("\n")), 5)
        for line in dot.split("\n"):
            if line.startswith('"red"'):
                self.assertTrue("color=blue" in line)
                self.assertTrue("weight=2" in line)
            elif line.startswith('"violent"'):
                self.assertTrue("color=red" in line)
                self.assertTrue("weight=2" in line)
            elif line.startswith('"green"'):
                self.assertTrue("color=red" in line)
                self.assertTrue("weight=2" in line)

    def test_graph_node_name(self):
        a = Dataset("a")
        b = Dataset("b")
        c = Dataset("c")
        d = Dataset("d")
        d.dependson(c)
        c.dependson(a, b)

        dot = depgraph.graphviz(d, node_id=lambda d: d.name.upper())
        self.assertEqual(len(dot.split("\n")), 5)
        self.assertTrue('"C" -> "D"' in dot)
        self.assertTrue('"A" -> "C"' in dot)
        self.assertTrue('"B" -> "C"' in dot)

if __name__ == "__main__":
    unittest.main()
