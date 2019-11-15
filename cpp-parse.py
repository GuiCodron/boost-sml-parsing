from __future__ import print_function

from toposort import toposort, toposort_flatten
import re
import os
import sys
import argparse
import clang

from clang.cindex import CompilationDatabase, Config, TranslationUnit, CursorKind
Config.set_library_path("/usr/lib/llvm-6.0/lib")


def get_tu(filename, compdb):
    args = [str(i) for i in compdb.getCompileCommands(filename)[0].arguments]
    args = args[1:-2]
    tu = TranslationUnit.from_source(filename, args=args)
    return tu


def get_compilation_args(filename, compdb):
    cmds = compdb.getCompileCommands(filename)
    if cmds is None:
        return None
    include_opts = ['-I', '-isystem', '-D',
                    '-internal-isystem', '-internal-externc-isystem', '--sysroot', '-std'
                    ]

    next_is_include = False
    compilation_args : list= []

    for i in range(len(cmds)):
        for arg in cmds[i].arguments:
            if not next_is_include:
                if arg in include_opts:
                    next_is_include = True
                    compilation_args += [arg]
                    continue
                for opt in include_opts:
                    if arg.startswith(opt):
                        compilation_args += [arg]
                        break
                continue
            compilation_args += [arg]
            next_is_include = False
    return compilation_args


def get_all_includes(filename, compdb):
    tu = get_tu(filename, compdb)
    includes = set()
    for inc in tu.get_includes():
        includes.add(inc.include.name)
    return includes


def get_cursor_id(cursor, showIDS=False, cursor_list=[]):
    if not showIDS:
        return None

    if cursor is None:
        return None

    # FIXME: This is really slow. It would be nice if the index API exposed
    # something that let us hash cursors.
    for i, c in enumerate(cursor_list):
        if cursor == c:
            return i
    cursor_list.append(cursor)
    return len(cursor_list) - 1


def get_info(node, maxDepth=None, depth=0):
    if maxDepth is not None and depth >= maxDepth:
        children = [c.spelling
                    for c in node.get_children()]
    else:
        children = [get_info(c, maxDepth, depth+1)
                    for c in node.get_children()]
    if node.kind == CursorKind.UNEXPOSED_EXPR:
        return children
    if node.kind == CursorKind.LAMBDA_EXPR:
        return "lambda_decl"
    d = {'kind': node.kind,
         'spelling': node.spelling,
         #  'type' : node.type.spelling,
         'xchildren': children}
    if node.spelling == 'state':
        d["type"] = node.type.spelling
    id = get_cursor_id(node)
    if node.is_definition():
        d['is_definition'] = node.is_definition()
    if id is not None:
        d['id'] = id
    def_id = get_cursor_id(node.get_definition())
    if def_id:
        d['id'] = def_id
    if node.spelling != node.displayname:
        d['displayname'] = node.displayname
    if node.get_usr():
        d['usr'] = node.get_usr()
    return d


def rec_search(node, s_fun, files=[], max_depth=None, depth=0, transition_tables=[]):
    if max_depth is not None and depth >= max_depth:
        return
    if len(files) > 0 and node.location.file is not None and str(node.location.file) not in files:
        # print("end_location", node.location.file)
        return

    if s_fun(node):
        transition_tables.append(node)

    for c in node.get_children():
        rec_search(c, s_fun, files, max_depth, depth + 1, transition_tables)

    return transition_tables


def rec_spelling(node, d=None):
    if d is None:
        d = {}
    if node.kind == CursorKind.UNEXPOSED_EXPR:
        for c in node.get_children():
            rec_spelling(c, d)
    elif node.kind == CursorKind.LAMBDA_EXPR:
        d["lambda_decl"] = {}
    else:
        node_name = node.spelling

        d[node_name] = []
        for child in node.get_children():
            child_dict = {}
            d[node_name].append(child_dict)
            rec_spelling(child, child_dict)

    return d


def bfs(func, to_process=[]):
    nexts = []
    for d in to_process:
        ret = func(d)
        if ret is not None:
            return d
        if len(d.c) is not None:
            nexts += d.c

    if len(nexts) == 0:
        return None

    return bfs(func, nexts)


def rep_struct(s):
    return str(s).replace("struct ", "")


def get_state_name(node, is_initial=False):
    if node.name == "operator*":
        is_initial = True
    if node.name == "X":
        return (is_initial, "[*]")
    if node.name == "state":
        return (is_initial, rep_struct(node.c[0].name))
    if len(node.c) == 0:
        return (is_initial, rep_struct(node.name))
    return get_state_name(node.c[0], is_initial)


def get_source(transition):
    def has_make_transition_table(node):
        if node.name == "make_transition_table":
            return True
        else:
            return None

    if bfs(has_make_transition_table, [transition]):
        return None

    node = None
    if transition.name == "operator<=":
        node = transition.c[2]
    else:
        node = transition.c[0]

    return get_state_name(node)


def get_target(transition):
    def get_target_node(d):
        if d.name in ["operator=", "operator<="]:
            return True
        else:
            return None
    target_node = bfs(get_target_node, [transition])

    if target_node is None:
        return None

    if target_node.name == "operator<=":
        target_node = target_node.c[0]
    else:
        target_node = target_node.c[2]

    return get_state_name(target_node)


def get_event(transition):
    def get_event_node(d):
        if d.name in ["event", "on_entry", "on_exit"]:
            return True
        else:
            return None
    event_node = bfs(get_event_node, [transition])

    if event_node is None:
        return None

    if event_node.name in ["on_entry", "on_exit"]:
        return event_node.name

    return rep_struct(event_node.c[0].name)


def get_guard(transition):
    def get_guard_node(d):
        if d.name == "operator[]":
            return True
        else:
            return None
    guard_node = bfs(get_guard_node, [transition])

    if guard_node is None:
        return None
    guard_node = guard_node.c[2]
    guard_repr = ""

    def parse_guard(node):
        if node.name == "operator!":
            return "!" + parse_guard(node.c[0])
        if node.name == "operator&&":
            return parse_guard(node.c[0]) + " && " + parse_guard(node.c[2])
        if node.name == "operator||":
            return parse_guard(node.c[0]) + " || " + parse_guard(node.c[2])
        if node.name == "operator()" and node.c[0].name == "call":
            return parse_guard(node.c[2])
        if node.name == "":
            return "(" + parse_guard(node.c[0]) + ")"
        if len(node.c) == 0:
            return node.name
        print(node)
        raise Exception("Action parsing error: " + node)

    return parse_guard(guard_node)


def get_action(transition):
    def get_action_node(d):
        if d.name == "operator/":
            return True
        else:
            return None
    action_node = bfs(get_action_node, [transition])

    if action_node is None:
        return None
    action_node = action_node.c[2]
    guard_repr = ""

    def parse_action(node):
        if node.name == "operator,":
            return parse_action(node.c[0]) + ", " + parse_action(node.c[2])
        if node.name == "operator()" and node.c[0].name == "call":
            return parse_action(node.c[2])
        if node.name == "":
            return "(" + parse_action(node.c[0]) + ")"
        return node.name
        # if len(node.c) == 0:
        # raise Exception("Action parsing error", node, node.node)

    return parse_action(action_node)


def parse_transition(node):
    state_refs = []
    source_ret = get_source(node)
    if source_ret is None:
        return None, state_refs

    transition_repr = ""

    is_initial, source_name = source_ret
    if is_initial:
        transition_repr += "[*] --> {}\n".format(source_name)
    transition_repr += source_name

    state_refs += [source_name]

    target_ret = get_target(node)
    if target_ret is not None:
        state_refs += [target_ret[1]]
        transition_repr += " --> " + target_ret[1]

    event_ret = get_event(node)
    guard_ret = get_guard(node)
    action_ret = get_action(node)

    if event_ret or action_ret or guard_ret:
        transition_repr += " :"
    if event_ret is not None:
        transition_repr += " " + event_ret

    if guard_ret:
        transition_repr += " [" + guard_ret + "]"

    if action_ret:
        transition_repr += " / " + action_ret
    return transition_repr, state_refs


def get_transitions(node, transition_store=[]):
    for child in node.get_children():
        if child.kind == CursorKind.UNEXPOSED_EXPR:
            get_transitions(child, transition_store)
        else:
            transition_store.append(child)
    return transition_store


def parse_transition_table(node, namespaces_prefix):
    transitions = []
    transitions = get_transitions(node, transitions)
    state_refs = []

    transition_table_repr = ""
    for transition in transitions:
        node = NodeRepr(rec_spelling(transition), namespaces_prefix)

        parsed_transition, transition_state_refs = parse_transition(node)
        if parsed_transition is not None:
            transition_table_repr += parsed_transition + "\n"
            state_refs += transition_state_refs

    return transition_table_repr, set(state_refs)


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


def regex_search(pattern):
    def f(node):
        return re.match(pattern, node.spelling)
    return f


def transition_search(node):
    return node.kind == CursorKind.CALL_EXPR and node.spelling == 'make_transition_table'


def sm_search(node):
    if node.kind != CursorKind.STRUCT_DECL:
        return False
    sm_creation = [n for n in node.get_children() if n.displayname ==
                   'operator()()']
    if len(sm_creation) == 0:
        return False

    return len(rec_search(node, transition_search, [], transition_tables=[])) != 0


def get_diag_info(diag):
    return {'severity': diag.severity,
            'location': diag.location,
            'spelling': diag.spelling,
            'ranges': diag.ranges,
            'fixits': diag.fixits}


def main():

    compile_commands_file = sys.argv[1]
    cpp_file = sys.argv[2]
    namespaces_prefix = sys.argv[3].split(',')
    namespaces_prefix.sort(key=lambda x: -len(x))

    compilationDB = CompilationDatabase.fromDirectory(
        os.path.dirname(compile_commands_file))
    index = clang.cindex.Index.create()

    compile_args = get_compilation_args(cpp_file, compilationDB)
    if compile_args is None:
        print(f"No compile command for file: {cpp_file}")

    # print(' '.join(list(compile_args[0].arguments)[1:]))

    tu = index.parse(cpp_file, compile_args)

    for diag in tu.diagnostics:
        epprint(get_diag_info(diag))

    sm_bases = []
    rec_search(tu.cursor, sm_search, [], transition_tables=sm_bases)

    type_map = {}
    def get_hash_list(node):
        if node.is_definition() and node.kind == CursorKind.STRUCT_DECL:
            type_map[node.type.spelling] = get_info(node)
        return False

    rec_search(tu.cursor, get_hash_list, [], transition_tables=[])
    pprint(type_map)
    exit(1)
    # transition_tables = []
    # rec_search(tu.cursor, transition_search, [],
    #            transition_tables=transition_tables)

    def get_sm(sm_list, sm_name):
        return [e for e in sm_list if e[0].spelling == sm_name][0]

    state_machines = []
    state_machines_graph = {}
    for sm_base in sm_bases:
        tt = rec_search(sm_base, transition_search, transition_tables=[])[0]
        print(tt)
        tt_repr, tt_refs = parse_transition_table(tt, namespaces_prefix)
        print(sm_base, tt_repr, tt_refs)
        state_machines.append([sm_base, tt_repr, tt_refs])
        state_machines_graph[sm_base.spelling] = tt_refs


    graph_view = list(toposort(state_machines_graph))
    print(graph_view)

    graph_view = graph_view[1:]
    for sm_names in graph_view:
        for sm_name in sm_names:
            sm = get_sm(state_machines, sm_name)
            new_repr = ""
            for sub_sm_name in [e for e in sm[2] if e in state_machines_graph]:
                sub_sm = get_sm(state_machines, sub_sm_name)
                new_repr += "state " + sub_sm_name + " {\n"
                for line in sub_sm[1].splitlines():
                    new_repr += "\t" + line + "\n"
                new_repr += "}\n"
            sm[1] = new_repr + sm[1]

    print("@startuml")
    for sm_name in graph_view[-1]:
        sm = get_sm(state_machines, sm_name)
        print(sm[1])
    print("@enduml")


main()
