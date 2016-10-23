#!/usr/bin/python3
#####################################################################
# Convert GEDCOM family tree to a directed (sub)graph. Usage:
#   python gedcom2graph.py input.ged output.html
#####################################################################
import sys
import re
import graph_tool
import graph_tool.search
import graph_tool.topology

if sys.hexversion < 0x030000F0:
    sys.exit("ERROR: Python 3 is needed to run this program")

if len(sys.argv) < 3 :
    sys.exit("USAGE: gedcom2graph.py input.ged output.html")

class Counter(graph_tool.search.DFSVisitor):

    def __init__(self, graph):
        self.graph = graph
        self.roots_from_id = {}
        self.count = None
        self.root = None

    def _record(self, v):
        if v not in self.roots_from_id:
            self.roots_from_id[v] = []
        self.roots_from_id[v].append(self.root)
        self.count += 1

    def discover_vertex(self, v):
        if self.graph.vp.id[v][0] == 'I':
            self._record(v)
        if self.graph.vp.id[v][0] == 'F':
            m = self.graph.vp.mother[v]
            if m is not None:
                self._record(m)

    def start_vertex(self, v):
        self.count = 0
        self.root = v

class Printer(graph_tool.search.DFSVisitor):

    refs_from_id = {}

    def __init__(self, graph):
        self.graph = graph
        self.level = 0
        self.lines = []

    def discover_vertex(self, v):
        if self.graph.vp.id[v][0] == 'I':
            line = '│ '*(self.level-1) + '├ ' if self.level else ''
            self.lines.append(line + self.graph.format_name(v))
            self.level += 1
        if self.graph.vp.id[v][0] == 'F':
            m = self.graph.vp.mother[v]
            if m is not None:
                line = '│ '*(self.level-1) + '│'
                self.lines.append(line + '+' + self.graph.format_name(m))

    def finish_vertex(self, v):
        if self.graph.vp.id[v][0] == 'I':
            self.level -= 1
            if self.lines:
                last = self.lines[-1]
                pos = self.level * 2
                if last[pos] == '├':
                    last = last[:pos] + '└' + last[pos+1:]
                elif last[pos] == '│':
                    last = last[:pos] + '╵' + last[pos+1:]
                self.lines[-1] = last


class TheGraph(graph_tool.Graph):

    def __init__(self):
        super().__init__()
        self._vertex_by_id = {}
        self.vp.id = self.new_vertex_property('string')
        # for @I…@ vertices
        for key in ['givn', 'surn', 'birt', 'birp', 'deat', 'deap']:
            self.vp[key] = self.new_vertex_property('string')
        # for @F…@ vertices
        for key in ['date', 'plac']:
            self.vp[key] = self.new_vertex_property('string')
        # father -> family and family -> children
        self.ep.male = self.new_edge_property('bool')
        # family -> mother
        self.vp.mother = self.new_vertex_property('object')

    def by_id(self, id: str):
        if id in self._vertex_by_id:
            v = self._vertex_by_id[id]
        else:
            v = self.add_vertex()
            self.vp.id[v] = id
            self._vertex_by_id[id] = v
        return v

    def format_name(self, v):
        name = self.vp.givn[v]
        if not name:
            name = 'NN.'
        if self.vp.surn[v]:
            name += ' ' + self.vp.surn[v]
        return name


g = TheGraph()
inpath, outpath = sys.argv[1:3]

lastid = last0 = last1 = None
regex = re.compile('^(\d+)\s+(\S+)(.*)$')
regid = re.compile('^@([A-Z]\d+)@$')
with open(inpath, 'rt') as infile :
    for line in infile.readlines() :
        match = regex.match(line.strip())
        if match is None :
            continue
        level = int(match.group(1))
        ident = match.group(2)
        value = match.group(3).strip()

        if level == 0 :
            idmatch = regid.match(ident)
            lastid = last0 = last1 = None
            if idmatch is not None :
                lastid = idmatch.group(1)
                last0 = value

        if level == 1 and last0 is not None :
            last1 = ident

        if level == 1 and last1 == 'DEAT' :
            g.vp.deat[g.by_id(lastid)] = ''

        if level == 2 and last0 == 'INDI' and last1 == 'NAME' :
            if ident == 'GIVN' :
                g.vp.givn[g.by_id(lastid)] = value
            if ident == 'SURN' :
                g.vp.surn[g.by_id(lastid)] = value

        if level == 2 and ident == 'DATE' :
            parts = value.split()
            if len(parts) >= 2 :
                parts[-2] = {
                    'JAN': '01',
                    'FEB': '02',
                    'MAR': '03',
                    'APR': '04',
                    'MAY': '05',
                    'JUN': '06',
                    'JUL': '07',
                    'AUG': '08',
                    'SEP': '09',
                    'OCT': '10',
                    'NOV': '11',
                    'DEC': '12',
                }[parts[-2]]
            # TODO wyciągać miesiąc i rok, jeśli są
            year = '.'.join(parts[::-1])
            if last0 == 'INDI' and last1 == 'BIRT' :
                g.vp.birt[g.by_id(lastid)] = year
            if last0 == 'INDI' and last1 == 'DEAT' :
                g.vp.deat[g.by_id(lastid)] = year
            if last0 == 'FAM' and last1 == 'MARR' :
                g.vp.date[g.by_id(lastid)] = year

        if level == 2 and last0 == 'INDI' and last1 == 'BIRT' and ident == 'PLAC' :
            g.vp.birp[g.by_id(lastid)] = value
        if level == 2 and last0 == 'INDI' and last1 == 'DEAT' and ident == 'PLAC' :
            g.vp.deap[g.by_id(lastid)] = value
        if level == 2 and last0 == 'FAM' and last1 == 'MARR' and ident == 'PLAC' :
            g.vp.plac[g.by_id(lastid)] = value

        if level == 1 and last0 == 'FAM' :
            other = value.strip('@')
            if ident == 'HUSB':
                e = g.add_edge(g.by_id(other), g.by_id(lastid))
                g.ep.male[e] = True
            if ident == 'WIFE':
                e = g.add_edge(g.by_id(other), g.by_id(lastid))
                g.vp.mother[g.by_id(lastid)] = g.by_id(other)
            if ident == 'CHIL' :
                e = g.add_edge(g.by_id(lastid), g.by_id(other))
                g.ep.male[e] = True

for v in g.vertices():
    if g.vp.id[v][0] == 'F':
        mother = None
        father = None
        for parent in v.in_edges():
            if g.ep.male[parent]:
                father = parent
            else:
                mother = parent
        if mother is not None:
            if father is None:
                g.ep.male[mother] = True
                g.vp.mother[v] = None
            elif mother.source().in_degree() and not father.source().in_degree():
                g.ep.male[mother] = True
                g.ep.male[father] = False
                g.vp.mother[v] = father.source()

gmale = graph_tool.GraphView(g, efilt=g.ep.male)

counter = Counter(g)
counts = {}
for v in g.vertices():
    if v.in_degree() == 0:
        graph_tool.search.dfs_search(gmale, v, counter)
        counts[v] = counter.count

with open(outpath, 'wt') as f:
    f.write('<!DOCTYPE html>\n<head><meta charset="utf-8" /></head>\n<body style="font-family:\'DejaVu Serif\', serif">\n')
    for v, count in [(k, counts[k]) for k in sorted(counts, key=counts.get, reverse=True)]:
        printer = Printer(g)
        graph_tool.search.dfs_search(gmale, v, printer)
        if len(printer.lines) > 1:
            f.write('<p>\n')
            for line in printer.lines:
                f.write(line+"<br>\n")
            f.write('</p>\n')
    f.write('</body>\n</html>\n')
