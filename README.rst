Dependency resolution for datasets
==================================

|Build Status|

*depgraph* is a tiny (<500 LOC) Python library for expressing networks
of datasets and their relationships. In this way, it is superficially
similar to `Airflow <https://github.com/apache/incubator-airflow>`__ and
`Luigi <https://github.com/spotify/luigi>`__, although those tools
contain significantly more functionality.

Networks are declared in terms of the relationships (graph edges)
between source and target datasets (graph nodes). Target datasets can
then report sets of precursor datasets in the correct order. This makes
it simple to throw together a build script and construct dependencies,
sequentially or with parallelization.

Traditionally, each ``Dataset`` is designed to correspond to a file. A
``DatasetGroup`` class handles cases where multiple files can be
considered a single file (e.g. a binary data file and its XML metadata).

    Different kinds of resources, such as database tables, can be used
    as long as they can be queried to determine whether they exist (how
    how old they are, in order to tak advantage of age-based incremental
    building).

When a ``Dataset`` requires a different dataset to be built to satisfy
its dependencies, it provides a reason, such as:

-  the ``Dataset`` is missing, and so must be built
-  the ``Dataset`` is out of date

*depgraph* is intended to be a reusable component for constructing
scientific dataset build tools. Important considerations for such a
build tool are that it must:

-  permit `reproducible
   analysis <http://science.sciencemag.org/content/334/6060/1226.long>`__
-  be documenting so that `a workflow can be easily
   reported <http://www.ontosoft.org/gpf/node/1>`__
-  perform fast rebuilds to enable experimentation

Beyond the standard library, *depgraph* has no dependencies of its own,
so it is easy to include in projects running on a laptop, on a large
cluster, or in the cloud. *depgraph* supports modern Python
implementations (Python 2, Python 3, PyPy), and works on Linux, OS X,
and Windows.

Important parts
---------------

``Dataset`` defines an individual data product, represented by a
filename, *name*. Additional keyword arguments may be provided in order
to facilitate the build process.

The ancestors of a dataset can be retrieved with ``Dataset.parents(n)``,
where *n* is the number of generations to include. *n=0* means include
only the direct parents, while *n=1* includes grandparents. *n=-1*
includes every ancestor. ``Dataset.roots()`` returns the top-level
ancestors, i.e. those with no additional parents.

Similarly, ``Dataset.children(n)`` yields the descendants of a dataset,
if any.

Relationships are defined with ``Dataset.dependson(obj)``, where *obj*
is another ``Dataset`` instance. Relationships can be defined
programmatically to construct large dependency graphs.

A user defined ``build(dataset, reason)`` function (name unimportant)
takes a dataset and constructs it based on its ancestors and any other
attributes of the ``Dataset``. The *reason* is a ``Reason`` object that
specifies the motivation for a build step.

The ``depgraph.buildall()`` function or ``Dataset.buildnext()`` method
can be used to obtain ancestor datasets and reason pairs to feed to the
``build()`` function. Alternatively, the ``build()`` function can be
decorated with the ``buildmanager`` decorator, which creates a function
that automatically constructs a dataset by assembling its dependencies
in order (see the examples below).

Complex dependency graphs can be visualized by using the ``graphviz()``
function, which returns a `DOT
language <http://www.graphviz.org/content/dot-language>`__ string
encoding the visual graph.

Example
-------

Declare a set of dependencies resembling the graph below:

::

         R0      R1      R2      R3         [raw data]
           \     /       |       |
             DA0         DA1    /
                 \      /  \   /
                    DB0     DB1
                     \     / |  \
                      \   /  |   \
                       DC0  DC1  DC2        [products]

.. code:: python

    from depgraph import Dataset, buildmanager

    # Define Datasets
    # Use an optional keyword `tool` to provide a key instructing our build tool
    # how to assemble this product. Here we've used strings, but another pattern
    # would be to provide a callback function
    R0 = Dataset("data/raw0", tool="read_csv")
    R1 = Dataset("data/raw1", tool="read_csv")
    R2 = Dataset("data/raw2", tool="database_query")
    R3 = Dataset("data/raw3", tool="read_hdf")

    DA0 = Dataset("step1/da0", tool="merge_fish_counts")
    DA1 = Dataset("step1/da1", tool="process_filter")

    DB0 = Dataset("step2/db0", tool="join_counts")
    DB1 = Dataset("step2/db1", tool="join_by_date")

    DC0 = Dataset("results/dc0", tool="merge_model_obs")
    DC1 = Dataset("results/dc1", tool="compute_uncertainty")
    DC2 = Dataset("results/dc2", tool="make_plots")

    # Declare dependency relationships so that depgraph and determine the order of
    # the build
    DA0.dependson(R0, R1)
    DA1.dependson(R2)
    DB0.dependson(DA0, DA1)
    DB1.dependson(DA1, R3)
    DC0.dependson(DB0, DB1)
    DC1.dependson(DB1)
    DC2.dependson(DB1)

    # Option 1:
    # Define a function that builds individual dependencies. The *buildmanager*
    # decorator transforms it into a loop that builds all dependencies above a
    # target
    @buildmanager
    def batchbuilder(dependency, reason):
        # [....]
        return exitcode

    batchbuilder(DC1)

    # Option 2:
    # Implement the build loop manually
    from depgraph import buildall

    def build(dependency, reason):
        # This may have the same logic as `batchbuilder` above, but we
        # will call it directly rather than wrapping it in @buildmanager
        # [....]
        return exitcode

    for stage in buildall(DC1):

        # A build stage is a list of dependencies whose own dependencies are met and
        # that are independent, i.e. they can be built in parallel

        for dep, reason in stage:

            # Each target is a dataset with a 'name' attribute and whatever
            # additional keyword arguments where defined with it.
            # The 'reason' is a depgraph.Reason object that codifies why a
            # particular target is necessary (e.g. it's out of date, it's missing
            # and required by a subsequent target, etc.)
            print("Building {0} with {1} because {2}".format(dep.name, dep.tool,
                                                             reason))

            # Call a function or start a subprocess that will result in the
            # target being built and saved to a file
            return_val = build(dep, reason)

            # Perform logging, clean-up, or error handling operations
            # [....]

Changes
-------

0.4
~~~

-  Performance improvements
-  ``buildall`` generator function, which is more efficient than
   repeatedly calling ``Dataset.buildnext()``

0.3
~~~

-  Cyclic graph detection
-  Graphviz export

0.2
~~~

-  Rewrite, dropping ``DependencyGraph`` and making ``Dataset`` the
   primary class

0.1
~~~

-  First version, copied from ``depchain`` module of asputil package

.. |Build Status| image:: https://travis-ci.org/njwilson23/depgraph.svg?branch=master
   :target: https://travis-ci.org/njwilson23/depgraph
