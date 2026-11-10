import re

class Sym(str):
    """Bare (unquoted) s-expression atom."""
    pass

_tok = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))', re.S)

def parse(text):
    pos = 0
    stack = [[]]
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            l = stack.pop()
            stack[-1].append(l)
        elif m.group(3) is not None:
            raw = m.group(3)[1:-1]
            stack[-1].append(re.sub(r'\\(.)', lambda mm: {'n': '\n', '"': '"', '\\': '\\'}.get(mm.group(1), '\\' + mm.group(1)), raw))
        elif m.group(4) is not None:
            stack[-1].append(Sym(m.group(4)))
    return stack[0][0]

def find(node, name):
    return [x for x in node if isinstance(x, list) and x and x[0] == name]

def first(node, name, default=None):
    f = find(node, name)
    return f[0] if f else default

def prop(sym, name):
    for p in find(sym, 'property'):
        if p[1] == name:
            return p[2]
    return None

def dump(node, indent=0):
    """Serialise back to KiCad-style s-expression text."""
    if isinstance(node, list):
        if not node:
            return '()'
        head = node[0]
        parts = []
        simple = all(not isinstance(x, list) for x in node)
        if simple:
            return '(' + ' '.join(dump(x) for x in node) + ')'
        out = '(' + dump(head)
        for x in node[1:]:
            if isinstance(x, list):
                out += '\n' + '\t' * (indent + 1) + dump(x, indent + 1)
            else:
                out += ' ' + dump(x)
        out += '\n' + '\t' * indent + ')'
        return out
    if isinstance(node, Sym):
        return str(node)
    if isinstance(node, str):
        return '"' + node.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    return str(node)
