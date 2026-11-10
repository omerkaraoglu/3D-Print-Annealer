import re
def parse(s):
    tokens=re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+',s)
    stack=[[]]
    for t in tokens:
        if t=='(': stack.append([])
        elif t==')':
            x=stack.pop(); stack[-1].append(x)
        else: stack[-1].append(t[1:-1] if t.startswith('"') else t)
    return stack[0][0]
def find(node,key):
    return [x for x in node if isinstance(x,list) and x and x[0]==key]
def first(node,key):
    f=find(node,key); return f[0] if f else None
