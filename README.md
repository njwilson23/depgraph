# Dependency resolution for datasets

![Travis status](https://travis-ci.org/njwilson23/depgraph.svg?branch=master)

`depgraph` is a tiny Python library for expressing networks of dependencies
repired to construct datasets. Networks are declared in terms of the
relationships between source and target datasets (network graph edges).
`depgraph` can then report descendants and parents for any particular node and
direct builds in a manner similar to `make`. When a `DependencyGraph` object
returns a dataset that must be built, it provides a reason, such as:

- the dataset is missing
- the dataset is out of date and required by another dataset
- the dataset is a target dataset

`depgraph` is intended to be a component for assembling dataset build tools.
Important considerations for such a build tool are that it must:

- permit reproducible analysis
- be documenting
- perform fast rebuilds to enable experimentation

`depgraph` contains the following classes:

- `depgraph.DependencyGraph`
- `depgraph.Dataset`
- `depgraph.DatasetGroup`
- `depgraph.Reason`
