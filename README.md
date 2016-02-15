# Dependency resolution for dataset pipelines

`depgraph` is a tiny Python library for expressing networks of dependencies for
constructing datasets. Networks are declared in terms of the relationships
beween raw, intermediate, and target datasets (network graph edges). `depgraph`
can then report descendents and parents for any particular dataset and direct
builds in a manner similar to `make`. When a `DependencyGraph` object returns a
dataset that must be built, it provides a reason, such as:

- the dataset is missing
- the dataset is out of date and required by another dataset
- the dataset is a target dataset

`depgraph` contains the following classes:

- `depgraph.DependencyGraph`
- `depgraph.Dependency`
- `depgraph.Reason`
