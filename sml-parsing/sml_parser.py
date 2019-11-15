from typing import Optional, List

import clang_config

import clang

from clang.cindex import CompilationDatabase, TranslationUnit, CursorKind, Cursor


class SMLState():
    def __init__(self, node: Cursor):
        pass


class SMLTransition():
    def __init__(self, node: Cursor):
        self.src_state: Cursor = None
        self.dest_state: Optional[Cursor] = None
        self.actions: Optional[List[Cursor]] = None
        self.guards Optional[List[Cursor]] = None
        self.event: Optional[Cursor] = None

    def to_string(self) -> str:
        return ""


class NodeRepr():
    def __init__(self, source_node, namespaces_prefix):
        name, childs = next(iter(source_node.items()))
        for namespace in namespaces_prefix:
            name = name.replace(namespace, '')
        name = name.replace("::", '_')
        self.node = source_node
        self.name = name
        self.c = [NodeRepr(c, namespaces_prefix) for c in childs]

    def __repr__(self):
        return {self.name: self.c}.__repr__()
