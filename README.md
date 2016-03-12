# Dependency resolution for dataset pipelines

`depgraph` is a tiny Python library for expressing networks of dependencies for
constructing datasets. Networks are declared in terms of the relationships
between raw, intermediate, and target datasets (network graph edges). `depgraph`
can then report descendants and parents for any particular dataset and direct
builds in a manner similar to `make`. When a `DependencyGraph` object returns a
dataset that must be built, it provides a reason, such as:

- the dataset is missing
- the dataset is out of date and required by another dataset
- the dataset is a target dataset

`depgraph` is intended to be a component for assembling dataset build tools.
Important considerations for such a build tool are that it must:

- permit reproducible analysis
- perform fast rebuilds to enable experimentation
- be documenting

`depgraph` contains the following classes:

- `depgraph.DependencyGraph`
- `depgraph.Dataset`
- `depgraph.DatasetGroup`
- `depgraph.Reason`
