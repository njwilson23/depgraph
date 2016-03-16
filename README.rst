Dependency resolution for datasets
==================================

.. figure:: https://travis-ci.org/njwilson23/depgraph.svg?branch=master
   :alt: Travis status

   Travis status

``depgraph`` is a tiny Python library for expressing networks of
dependencies required to construct datasets. Networks are declared in
terms of the relationships (graph edges) between source and target
datasets (graph nodes). Target datasets can then report sets of
precursor datasets in the correct order. This makes it simple to throw
together build script and construct dependencies in parallel.

Traditionally, each ``Dataset`` is designed to correspond to a file. A
``DatasetGroup`` class handles cases where multiple files can be
considered a single file (e.g. a binary data file and its XML metadata).

When a ``Dataset`` requires a different dataset to be built to satisfy
its dependencies, it provides a reason, such as:

-  the dependency is missing
-  the dependency is out of date

``depgraph`` is intended to be a reusable component for assembling
scientific dataset build tools. Important considerations for such a
build tool are that it must:

-  perform fast rebuilds to enable experimentation
-  permit `reproducible
   analysis <http://science.sciencemag.org/content/334/6060/1226.long>`__
-  be documenting so that `a workflow can be easily
   reported <http://www.ontosoft.org/gpf/node/1>`__

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

    from depgraph import Dataset

    # Define Datasets
    # use an optional keyword `tool` to provide a key instructing our build tool
    # how to assemble this product
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

    # Declare relationships
    da0.dependson(raw0, raw1)
    da1.dependson(raw2)
    db0.dependson(da0, da1)
    db1.dependson(da1, raw3)
    dc0.dependson(db0, db1)
    dc1.dependson(db1)
    dc2.dependson(db1)

    # Query buildsteps to build a product (DC1)
    while True:
        targets = list(DC1.buildnext())

        if len(targets) == 0:
            break

        for target, reason in targets:
            # Each target is a dataset with a 'name' attribute and whatever
            # additional keyword arguments where defined with it.
            # The 'reason' is a depgraph.Reason object that codifies why a
            # particular target is necessary (e.g. it's out of date, it's missing,
            # and required by a subsequent target, etc.)
            print("Building {0} with {1} because {2}".format(target.name,
                                                             target.tool,
                                                             reason))
            # Call a function or start a subprocess that will result in the
            # target being built and saved to a file
            my_build_func(target.tool, target.name)
            # [...]
