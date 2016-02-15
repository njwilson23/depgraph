import os

def _lastmodified(a):
    return os.stat(a.name).st_mtime

def isolder(a, b):
    """ returns true if dependency *a* was last modified before dependencies
    *b* """
    sa = os.stat(a.name)
    sb = os.stat(b.name)
    return sa.st_mtime < sb.st_mtime

def get_dependencies(target, relations):
    """ given *target*, return a list of dependencies sorted from top to bottom

    i.e. if the dependency graph looks like

                 target
               /        \
            raw0    intermediate
                        |
                       raw1

    returns either [intermediate, raw0, raw1]
            or     [raw0, intermediate, raw1]
    as these two options are considered equivalent
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

    def __init__(self, explanation):
        self._explanation = explanation

    def __str__(self):
        return self._explanation

class Dependency(object):

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

class DependencyGraph(object):
    """ Wraps a dictionary DependencyGraph.relations that encodes direct
    relationships between targets (keys) and lists of dependencies (values).
    """

    def __init__(self):
        self.relations = {}
        pass

    def add_dataset(self, name, dependencies=None):
        if name in self.relations:
            raise KeyError("{0} already listed in DependencyGraph")
        self.relations[name] = []
        if dependencies is not None:
            for dependency in dependencies:
                if dependency not in self.relations:
                    self.add_dataset(dependency)
                self.add_relation(name, dependency)
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

    def dependson(self, dep, depth=-1):
        """ Return the datasets that depend on *dep* """
        children = []
        for k, v in self.relations.items():
            if dep in v:
                children.append(k)
        if depth != 0:
            for child in children:
                children.extend(self.dependson(child, depth=depth-1))
        return set(children)

    def leadsto(self, target, depth=-1):
        """ Return the datasets that go into *target* """
        deps = [d for d in self.relations[target]]
        subdeps = []
        if depth != 0:
            for d in deps:
                subdeps.extend(self.leadsto(d, depth=depth-1))
        deps.extend(subdeps)
        return set(deps)

    def needsbuild(self, target):
        """ Returns a generator for products that must be built/rebuilt to
        satisfy a build chain. Uses `os.stat` to compare files and determine
        whether dependencies are out of date. """

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
                if (len(children) == 0) or isolder(ancestors[-1], children[0]):
                    yield (dep, because_required)

    def print_relations(self):
        for k in self.relations:
            print(k.name)
            for v in self.relations[k]:
                print("\t{0}".format(v.name))
        return

