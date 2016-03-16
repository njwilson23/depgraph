Dependency resolution for datasets
==================================

.. figure:: https://travis-ci.org/njwilson23/depgraph.svg?branch=master
   :alt: Travis status

   Travis status

``depgraph`` is a tiny Python library for expressing networks of
dependencies required to construct datasets. Networks are declared in
terms of the relationships between source and target datasets (network
graph edges). ``depgraph`` can then report descendants and parents for
any particular node and instruct builds in a manner similar to ``make``.
When a ``DependencyGraph`` object returns a dataset that must be built,
it provides a reason, such as:

-  the dataset is missing
-  the dataset is out of date and required by another dataset
-  the dataset is a target dataset

``depgraph`` is intended to be a component for assembling dataset build
tools. Important considerations for such a build tool are that it must:

-  permit reproducible analysis
-  be documenting
-  perform fast rebuilds to enable experimentation

``depgraph`` contains the following classes:

-  ``depgraph.DependencyGraph``
-  ``depgraph.Dataset``
-  ``depgraph.DatasetGroup``
-  ``depgraph.Reason``

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

    from depgraph import Dataset, DependencyGraph

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

    graph = DependencyGraph()

    # Declare relationships
    graph.add_dataset(da0, (raw0, raw1))
    graph.add_dataset(da1, (raw2,))
    graph.add_dataset(db0, (da0, da1))
    graph.add_dataset(db1, (da1, raw3))
    graph.add_dataset(dc0, (db0, db1))
    graph.add_dataset(dc1, (db1,))
    graph.add_dataset(dc2, (db1,))

    # Query buildsteps to build a product
    while True:
        targets = graph.buildable(DC1)

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
