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
    if isinstance(a, Dataset):
        mtime_a = os.stat(a.name).st_mtime
    elif isinstance(a, DatasetGroup):
        mtime_a = max(os.stat(d.name).st_mtime for d in a)
    else:
        raise TypeError("must be Dataset or DatasetGroup")

    if isinstance(b, Dataset):
        mtime_b = os.stat(b.name).st_mtime
    elif isinstance(b, DatasetGroup):
        mtime_b = min(os.stat(d.name).st_mtime for d in b)
    else:
        raise TypeError("must be Dataset or DatasetGroup")

    return mtime_a < mtime_b

def get_dependencies(target, relations):
    """ Given a target, return a list of dependencies sorted from top to bottom

    i.e. if the dependency graph looks like

                 target
               /        \
            raw0    intermediate
                        |
                       raw1

    returns either [intermediate, raw0, raw1]
            or     [raw0, intermediate, raw1]
    as these two options are considered equivalent

    Parameters
    ----------
    target : Dataset

    Returns
    -------
    list of Datasets
    """
    deps = []
    visited = []
    deps.extend(relations[target])

    nprev = 0
    n = len(deps)
    while n != nprev:
        for d in [a for a in deps]:
            if (d not in visited) and (d in relations):
                visited.append(d)
                deps.extend(relations[d])
        nprev = n
        n = len(deps)

    # remove duplicates
    kill = []
    for i, d in enumerate(deps[:-1]):
        if d in deps[i+1:]:
            kill.append(i)

    kill.reverse()
    for i in kill:
        deps.pop(i)
    return deps

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

class DatasetGroup(object):
    """ DatasetGroup represents multiple Dataset instances that are build
    together. For example, these might be a dataset and associated metadata.
    These should be built together, and dependent files are sensitive to
    updates in any member of a DatasetGroup.

    TODO:

    Currently, the main difference between this an Dataset is that isolder
    checks all parts. DependencyGraph could be modified so that calling
    add_relation or add_dataset with targets or dependencies already in an
    existing dependency group substitutes the group instead. (Counterpoint:
    this means that the order of adding dependencies matters (bad) unless
    adding a DatasetGroup forces the DependencyGraph to search existing
    dependencies for any overlap.)
    """

    __hash__ = object.__hash__

    def __init__(self, name, datasets, **kw):
        self.name = name
        self.datasets = datasets
        self._store = kw

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return (self.name == other.name) and (self._store == other._store)

    def __neq__(self, other):
        return not (self == other)

    def __iter__(self):
        for d in self.datasets:
            yield d

    def __getattr__(self, name):
        if name in self._store:
            return self._store[name]
        else:
            raise AttributeError("'{0}'".format(name))

class DependencyGraph(object):
    """ Wraps a dictionary DependencyGraph.relations that encodes direct
    relationships between targets (keys) and lists of dependencies (values).
    """

    def __init__(self):
        self.relations = {}
        pass

    def add_dataset(self, dataset, dependencies=None):
        if dataset in self.relations:
            raise KeyError("{0} already listed in DependencyGraph")
        self.relations[dataset] = []
        if dependencies is not None:
            for dependency in dependencies:
                if dependency not in self.relations:
                    self.add_dataset(dependency)
                self.add_relation(dataset, dependency)
        return

    def add_relation(self, target, dependency):
        if target not in self.relations:
            self.add_dataset(target)
        if dependency not in self.relations:
            self.add_dataset(dependency)
        self.relations[target].append(dependency)
        return

    def buildsteps(self, target):
        """ Return a list of dependencies in the order in which they should be
        obtained/built. """
        steps = [target]
        steps.extend(get_dependencies(target, self.relations))
        steps.reverse()
        return steps

    def dependson(self, dataset, depth=-1):
        """ Return the datasets that depend on a Dataset

        Parameters
        ----------
        dataset : Dataset
        depth : int, optional
            number of edges along which to search the DependencyGraph. Default
            is to search the entire graph above *dataset*.

        Returns
        -------
        set of Datasets
        """
        children = []
        for k, v in self.relations.items():
            if dataset in v:
                children.append(k)
        if depth != 0:
            for child in children:
                children.extend(self.dependson(child, depth=depth-1))
        return set(children)

    def leadsto(self, target, depth=-1):
        """ Return the datasets that go into a target Dataset

        Parameters
        ----------
        target : Dataset
        depth : int, optional
            number of edges along which to search the DependencyGraph. Default
            is to search the entire graph below *target*.

        Returns
        -------
        set of Datasets
        """
        deps = [d for d in self.relations[target]]
        subdeps = []
        if depth != 0:
            for d in deps:
                subdeps.extend(self.leadsto(d, depth=depth-1))
        deps.extend(subdeps)
        return set(deps)

    def getroots(self, target):
        """ Return the top-level (without dependencies) datasets that target
        depends on """
        roots = [parent for parent in self.leadsto(target)
                        if len(self.leadsto(parent, 0)) == 0]
        return set(roots)

    def buildable(self, target, _ancestors=None):
        """ Returns a generator that returns (Dataset, Reason) pairs
        representing products that can be built toward a target given the
        current graph state.

        These targets are necessary but not necessarily sufficient to build the
        target after a single iteration. Intended use is to call buildable
        repeatedly, building the target after each call, until the target can
        be built.

        Parameters
        ----------
        target : Dataset

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

        def walkbranch(dg, stem, ancestors, branches):
            """ Breadth-first search through branch for broken branches
            involving ancestors """
            for child in dg.dependson(stem, 0):
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

        ancestors = self.leadsto(target)
        branches = list(self.getroots(target))
        built = []

        while True:
            if len(branches) == 0:
                break

            for result in walkbranch(self, branches[0], ancestors, branches):
                if result not in built:
                    built.append(result)
                    yield result
            branches = branches[1:]




    def needsbuild(self, target):
        """ Returns a generator for products that must be built/rebuilt to
        satisfy a build chain. Uses `os.stat` to compare files and determine
        whether dependencies are out of date.

        Parameters
        ----------
        target : Dataset

        Yields
        ------
        (Dataset, Reason)
        """

        # start from the top and for each dependency:
        # - does it exist?
        #   - if so, is it younger than all of its parents?
        #       - if not, build
        #   - if not, is it a target?
        #       - if so, build
        #       - if not, are any of its children older than any of its parents?
        #           - if so, build

        because_is_target = Reason("it is the target")
        because_out_of_date = Reason("it is older than at least one of its parents")
        because_required = Reason("the target is descended from it")

        for dep in self.buildsteps(target):

            if os.path.isfile(dep.name):
                if any(isolder(dep, ancestor) for ancestor in self.leadsto(dep)
                                              if os.path.isfile(ancestor.name)):
                    yield (dep, because_out_of_date)

            elif dep == target:
                yield (dep, because_is_target)

            else:
                # determine whether a missing dependency needs to be built
                ancestors = sorted(filter(lambda d: os.path.isfile(d.name),
                                          self.leadsto(dep)), key=_lastmodified)
                children = sorted(filter(lambda d: os.path.isfile(d.name),
                                         self.dependson(dep)), key=_lastmodified)

                # compare youngest ancestor to oldest existing child
                if len(ancestors) == 0:
                    raise RuntimeError("build cannot be satisfied\n"
                    "{0} does not exist but has no dependencies".format(dep.name))

                if (len(children) == 0) or isolder(ancestors[-1], children[0]):
                    yield (dep, because_required)

    def print_relations(self):
        for k in self.relations:
            print(k.name)
            for v in self.relations[k]:
                print("\t{0}".format(v.name))
        return

