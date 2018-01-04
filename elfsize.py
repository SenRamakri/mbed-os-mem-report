#!/usr/bin/env python

from __future__ import print_function
from subprocess import check_output
from collections import OrderedDict
from os import path
import re, os, json

# arm-none-eabi-nm needs to be in the environment path
nm = "arm-none-eabi-nm"
nm_opts = "-l -S -C -f sysv"
default_datafile = "data-flare.js"
default_peakfile = "data-peak.js"
repo_root = path.dirname(path.abspath(__file__))
default_op = path.join(repo_root, "html", default_datafile)
default_op_peak = path.join(repo_root, "html", default_peakfile)

def add_node(root, node_path, node_size):
    node = root
    added = 0
    for p in node_path.split(os.sep):
        children = node["children"]
        if p not in [x['name'] for x in children]:
            add = {"name": p, "children": []}
            children.append(add)
            added = 1
            node = children[-1]
        else:
            p_index = [x['name'] for x in children].index(p)
            node = children[p_index]

    if added:
        node.pop("children")
        node['size'] = node_size

def output_to_file(fd, root, node_name):
    # write dict as json to output file
    s = json.dumps(dict(root), indent=4)
    fd.seek(0)
    fd.write("var %s = "%(str(node_name)))
    fd.write(s)
    fd.truncate()
