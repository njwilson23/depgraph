from .depgraph import get_descendent_edges, get_ancestor_edges

def graphviz(*datasets, **kwargs):
    """ Return a graphviz diagram in dot format describing the dependency
    graph.

    Parameters
    ----------
    *datasets : Dataset instances
    node_id : function(Dataset) -> str, optional
        Callable taking a Dataset and returning a name to use as a graphviz node
        id. Default is Dataset.name.
    style : function(Dataset) -> dict, optional
        Callable taking a Dataset and returning graphviz styling attributes.
        Default is bare styling.
    include : function(Dataset, Dataset) -> bool, optional
        Callable taking a Dataset and returning a boolean indicating whether a
        dataset should be included in the graph. Default is to include all
        datasets.

    Returns
    -------
    str : graphviz visualization in dot format
    """
    f_id = kwargs.get("node_id", lambda d: d.name)
    f_style = kwargs.get("style", lambda d1, d2: {})
    f_incl = kwargs.get("include", lambda d1, d2: True)

    # Make a list of edges (parent, child)
    edges = []
    for ds in datasets:
        edges.extend(e for e in get_descendent_edges(ds) if e not in edges)
        edges.extend(e for e in get_ancestor_edges(ds) if e not in edges)

    relations = []
    for e in edges:
        if f_incl(*e):
            s = f_style(*e)
            if len(s) != 0:
                s = " [{}]".format(",".join(["{}={}".format(*kv) for kv in s.items()]))
            relations.append("\"{}\" -> \"{}\"{}".format(f_id(e[0]), f_id(e[1]), s))

    dotstr = """strict digraph {{
  {0}
}}""".format("\n  ".join(relations))
    return dotstr


