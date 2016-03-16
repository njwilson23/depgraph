import os

def _lastmodified(a):
    return os.stat(a.name).st_mtime

def isolder(a, b):
    """ Returns true if Dataset *a* was last modified before Dataset *b*

    Parameters
    ----------
    a, b : Dataset

    Returns
    -------
    bool
    """
    if isinstance(a, DatasetGroup):
        mtime_a = max(os.stat(d.name).st_mtime for d in a)
    elif isinstance(a, Dataset):
        mtime_a = os.stat(a.name).st_mtime
    else:
        raise TypeError("must be Dataset or DatasetGroup")

    if isinstance(b, DatasetGroup):
        mtime_b = min(os.stat(d.name).st_mtime for d in b)
    elif isinstance(b, Dataset):
        mtime_b = os.stat(b.name).st_mtime
    else:
        raise TypeError("must be Dataset or DatasetGroup")

    return mtime_a < mtime_b

class Reason(object):
    """ A Reason describes why a build step is performed.

    Parameters
    ----------
    explanation : str
    """

    def __init__(self, explanation):
        self._explanation = explanation

    def __str__(self):
        return self._explanation

class Dataset(object):
    """ Dataset represents a dataset or a step along a dependency chain.

    Parameters
    ----------
    name : str
        imagined to be a filename

    Other keyword arguments are accessible as instance attributes.
    """

    __hash__ = object.__hash__

    def __init__(self, name, **kw):
        self.name = name
        self._parents = []
        self._children = []
        self._store = kw
        return

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return (self.name == other.name) and (self._store == other._store)

    def __neq__(self, other):
        return not (self == other)

    def __getattr__(self, name):
        if name in self._store:
            return self._store[name]
        else:
            raise AttributeError("'{0}'".format(name))

    def dependson(self, *datasets):
        for dataset in datasets:
            if dataset not in self.parents(0):
                self._parents.append(dataset)
                dataset._children.append(self)
            else:
                raise RedundantDeclaration("{0} already depends on "
                                           "{1}".format(dataset, self))

    def parents(self, depth=-1):
        """ Return the Datasets that depend on this Dataset """
        yielded = []
        for dataset in self._parents:
            if dataset not in yielded:
                yielded.append(dataset)
                yield dataset
            if depth != 0:
                for grandparent in dataset.parents():
                    if grandparent not in yielded:
                        yielded.append(grandparent)
                        yield grandparent

    def children(self, depth=-1):
        """ Return the Datasets that this Dataset depends on """
        yielded = []
        for dataset in self._children:
            if dataset not in yielded:
                yielded.append(dataset)
                yield dataset
            if depth != 0:
                for grandchild in dataset.children():
                    if grandchild not in yielded:
                        yielded.append(grandchild)
                        yield grandchild

    def buildnext(self):
        """ Generator for datasets that require building/rebuilding in order to
        build this (objective) Dataset, given the present state of the
        dependency graph.

        These targets are necessary but not necessarily sufficient to build the
        objective Dataset after a single iteration. Intended use is to call
        `buildnext` repeatedly, building the targets after each call, until the
        objective Dataset can be built.

        Yields
        ------
        (Dataset, Reason)
        """

        ParentMissing = Reason("the parent doesn't exist")
        ParentNewer = Reason("the parent is newer than the child")
        ChildMissing = Reason("the child doesn't exist")

        def needsbuild(parent, child):
            if not os.path.isfile(parent.name):
                return True, ParentMissing
            elif os.path.isfile(child.name) and isolder(child, parent):
                return True, ParentNewer
            elif not os.path.isfile(child.name):
                return True, ChildMissing
            else:
                return False, None

        def walkbranch(stem, ancestors, branches):
            """ Breadth-first search through branch for broken branches
            involving ancestors """
            for child in stem.children(0):
                if child not in ancestors:
                    continue

                build, reason = needsbuild(stem, child)

                if build:
                    if reason in (ParentNewer, ChildMissing):
                        yield child
                    elif reason == ParentMissing:
                        # This means that the stem of the current branch is
                        # missing. This shouldn't happen, because we
                        # started form the root and worked down, only
                        # adding branches
                        raise RuntimeError("impossible situation")

                elif not build:
                    if child not in branches:
                        branches.append(child)

        ancestors = list(self.parents())
        branches = list(self.roots())
        built = []

        while True:
            if len(branches) == 0:
                break

            for result in walkbranch(branches[0], ancestors, branches):
                if result not in built:
                    built.append(result)
                    yield result
            branches = branches[1:]
        return

    def roots(self):
        """ Generator for the roots (dependency-less parents) of this Dataset.
        """
        for dataset in self._parents:
            if len(dataset._parents) == 0:
                yield dataset
            else:
                for gp in dataset.roots():
                    yield gp

class DatasetGroup(Dataset):
    """ DatasetGroup represents multiple Dataset instances that are build
    together. For example, these might be a dataset and associated metadata.
    These should be built together, and dependent files are sensitive to
    updates in any member of a DatasetGroup.
    """

    __hash__ = object.__hash__

    def __init__(self, name, datasets, **kw):
        self.name = name
        self.datasets = datasets
        self._parents = []
        self._children = []
        self._store = kw

    def __iter__(self):
        for d in self.datasets:
            yield d

class RedundantDeclaration(Exception):
    def __init__(self, msg):
        self.message = msg

class CircularDependency(Exception):
    def __init__(self, msg):
        self.message = msg
