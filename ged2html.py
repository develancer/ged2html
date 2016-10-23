#!/usr/bin/python3
"""
Convert GEDCOM family tree to a directed (sub)graph.

Usage: python gedcom2graph.py input.ged output.html
"""
import sys
import re
try:
    from graph_tool import Graph, GraphView, Vertex
    from graph_tool.search import dfs_search, DFSVisitor
except ImportError:
    sys.exit('''ERROR: graph-tool library is needed to run this program
      (visit https://graph-tool.skewed.de/)''')

if sys.hexversion < 0x030000F0:
    sys.exit("ERROR: Python 3 is needed to run this program")

if len(sys.argv) < 3:
    sys.exit("USAGE: gedcom2graph.py input.ged output.html")


class Counter(DFSVisitor):
    """DFS visitor to count and index genealogical branches in the graph."""

    def __init__(self, graph: Graph):
        """
        Create a new Counter instance for a given graph.

        :param Graph graph: graph instance
        """
        self.graph = graph
        self.roots_per_vertex = {}
        self.count = None
        self.root = None

    def _record(self, v: Vertex):
        """
        Record given vertex as the member of the current branch.

        :param Vertex v: vertex
        """
        if v not in self.roots_per_vertex:
            self.roots_per_vertex[v] = []
        self.roots_per_vertex[v].append(self.root)
        self.count += 1

    def discover_vertex(self, v):
        """
        Invoke when a vertex is encountered for the first time.

        :param Vertex v: vertex
        """
        if self.graph.vp.gedid[v][0] == 'I':
            self._record(v)
        if self.graph.vp.gedid[v][0] == 'F':
            m = self.graph.vp.spouse[v]
            if m is not None:
                self._record(m)

    def start_vertex(self, v):
        """
        Invoke on the source vertex once before the start of the search.

        :param Vertex v: vertex
        """
        self.count = 0
        self.root = v


class Printer(DFSVisitor):
    """DFS visitor to convert given branch to HTML representation."""

    def __init__(self, graph: Graph, roots_per_vertex: dict,
                 num_from_root: dict):
        """
        Create new Printer instance for a given graph and preprocessed data.

        :param Graph graph: graph instance
        :param dict roots_per_vertex: a dictionary mapping every vertex into
        a set of root vertices of all branches it belongs to
        :param dict num_from_root: a dictionary mapping every branch root
        to the label (usually the number) of its branch
        """
        self.graph = graph
        self.roots_per_vertex = roots_per_vertex
        self.num_from_root = num_from_root
        self.level = 0
        self.lines = []
        self.root = None

    def _format_name(self, v: Vertex):
        """
        Return human-readable representation of the vertex.

        Generated description includes its connections to other diagrams.

        :param Vertex v: vertex instance
        :return str: HTML representation
        """
        result = self.graph.format_name(v)
        diagrams = []
        for root in self.roots_per_vertex[v]:
            if root != self.root and root in self.num_from_root:
                diagrams.append(self.num_from_root[root])
        if diagrams:
            result += (' → <span class=diagrams>'
                       + ', '.join(sorted(diagrams)) + '</span>')
        return result

    def discover_vertex(self, v):
        """
        Invoke when a vertex is encountered for the first time.

        :param Vertex v: vertex
        """
        if self.graph.vp.gedid[v][0] == 'I':
            line = '│ '*(self.level-1) + '├ ' if self.level else ''
            self.lines.append(line + self._format_name(v))
            self.level += 1
        if self.graph.vp.gedid[v][0] == 'F':
            m = self.graph.vp.spouse[v]
            if m is not None:
                line = '│ '*(self.level-1) + '┆'
                small = '⚭' + self.graph.vp.date[v]
                if self.graph.vp.plac[v]:
                    small += ' ('+self.graph.vp.plac[v]+')'
                line += '<span class=dates>' + small + '</span> '
                self.lines.append(line + self._format_name(m))

    def finish_vertex(self, v):
        """
        Invoke on each vertex u after all its descendants have been processed.

        :param Vertex v: vertex
        """
        if self.graph.vp.gedid[v][0] == 'I':
            self.level -= 1
            if self.lines:
                index = len(self.lines) - 1
                last = self.lines[index]
                pos = self.level * 2
                while (last[pos] == '│' and index > 0
                       and self.lines[index-1][pos] in ['├', '│', '┆']):
                    invis = '<span class=invis>│</span>'
                    self.lines[index] = last[:pos] + invis + last[pos+1:]
                    index -= 1
                    last = self.lines[index]
                if last[pos] == '├':
                    last = last[:pos] + '└' + last[pos+1:]
                elif last[pos] in ['│', '┆']:
                    last = last[:pos] + '╵' + last[pos+1:]
                self.lines[index] = last

    def start_vertex(self, v):
        """
        Invoke on the source vertex once before the start of the search.

        :param Vertex v: vertex
        """
        self.root = v


class TheGraph(Graph):
    """Subclass of graph_tool.Graph with GEDCOM-related functionality."""

    def __init__(self):
        """Create a new TheGraph instance."""
        super().__init__()
        self._vertex_by_id = {}
        self.vp.gedid = self.new_vertex_property('string')
        # for @I…@ vertices
        for key in ['givn', 'surn', 'birt', 'birp', 'deap']:
            self.vp[key] = self.new_vertex_property('string')
        self.vp.deat = self.new_vertex_property('object')  # default None
        # for @F…@ vertices
        for key in ['date', 'plac']:
            self.vp[key] = self.new_vertex_property('string')
        # main line of inheritance
        self.ep.main = self.new_edge_property('bool')
        # family -> spouse
        self.vp.spouse = self.new_vertex_property('object')

    def by_id(self, gedid: str):
        """
        Return node with given GEDCOM ID, or create one if it does not exist.

        :param str gedid: GEDCOM-style ID, e.g. I123
        :return Vertex: vertex with given GEDCOM ID
        """
        if gedid in self._vertex_by_id:
            v = self._vertex_by_id[gedid]
        else:
            v = self.add_vertex()
            self.vp.gedid[v] = gedid
            self._vertex_by_id[gedid] = v
        return v

    def format_name(self, v):
        """
        Return human-readable representation of the vertex.

        :param Vertex v: vertex instance
        :return str: HTML representation
        """
        name = self.vp.givn[v]
        if not name:
            name = 'NN.'
        if self.vp.surn[v]:
            name += ' ' + self.vp.surn[v]
        small = ''
        if self.vp.birt[v] or self.vp.birp[v]:
            small += ' *'+self.vp.birt[v]
            if self.vp.birp[v]:
                small += ' ('+self.vp.birp[v]+')'
        if self.vp.deat[v] is not None:
            small += ' †'+self.vp.deat[v]
            if self.vp.deap[v]:
                small += ' ('+self.vp.deap[v]+')'
        if small:
            name += '<span class=dates>' + small + '</span>'
        return name

    @classmethod
    def read_from_gedcom(cls, path):
        """
        Read graph data from GEDCOM file.

        :param str path: path to GEDCOM file
        :return TheGraph: graph instance
        """
        g = cls()
        lastid = last0 = last1 = None
        regex = re.compile('^(\d+)\s+(\S+)(.*)$')
        regid = re.compile('^@([A-Z]\d+)@$')
        with open(path, 'rt') as file:
            for line in file.readlines():
                match = regex.match(line.strip())
                if match is None:
                    continue
                level = int(match.group(1))
                ident = match.group(2)
                value = match.group(3).strip()

                if level == 0:
                    idmatch = regid.match(ident)
                    lastid = last0 = last1 = None
                    if idmatch is not None:
                        lastid = idmatch.group(1)
                        last0 = value

                if level == 1 and last0 is not None:
                    last1 = ident

                if level == 1 and last1 == 'DEAT':
                    g.vp.deat[g.by_id(lastid)] = ''

                if level == 2 and last0 == 'INDI' and last1 == 'NAME':
                    if ident == 'GIVN':
                        g.vp.givn[g.by_id(lastid)] = value
                    if ident == 'SURN':
                        g.vp.surn[g.by_id(lastid)] = value

                if level == 2 and ident == 'DATE':
                    parts = value.split()
                    if len(parts) >= 2:
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
                    if last0 == 'INDI' and last1 == 'BIRT':
                        g.vp.birt[g.by_id(lastid)] = year
                    if last0 == 'INDI' and last1 == 'DEAT':
                        g.vp.deat[g.by_id(lastid)] = year
                    if last0 == 'FAM' and last1 == 'MARR':
                        g.vp.date[g.by_id(lastid)] = year

                if level == 2:
                    if last0 == 'INDI' and last1 == 'BIRT' and ident == 'PLAC':
                        g.vp.birp[g.by_id(lastid)] = value
                    if last0 == 'INDI' and last1 == 'DEAT' and ident == 'PLAC':
                        g.vp.deap[g.by_id(lastid)] = value
                    if last0 == 'FAM' and last1 == 'MARR' and ident == 'PLAC':
                        g.vp.plac[g.by_id(lastid)] = value

                if level == 1 and last0 == 'FAM':
                    other = value.strip('@')
                    if ident == 'HUSB':
                        e = g.add_edge(g.by_id(other), g.by_id(lastid))
                        g.ep.main[e] = True
                    if ident == 'WIFE':
                        e = g.add_edge(g.by_id(other), g.by_id(lastid))
                        g.vp.spouse[g.by_id(lastid)] = g.by_id(other)
                    if ident == 'CHIL':
                        e = g.add_edge(g.by_id(lastid), g.by_id(other))
                        g.ep.main[e] = True

        for v in g.vertices():
            if g.vp.gedid[v][0] == 'F':
                to_mother = to_father = None
                mother = father = None
                for to_parent in v.in_edges():
                    if g.ep.main[to_parent]:
                        to_father = to_parent
                        father = to_father.source()
                    else:
                        to_mother = to_parent
                        mother = to_mother.source()
                if mother is not None:
                    if father is None:
                        g.ep.main[to_mother] = True
                        g.vp.spouse[v] = None
                    elif mother.in_degree() and not father.in_degree():
                        g.ep.main[to_mother] = True
                        g.ep.main[to_father] = False
                        g.vp.spouse[v] = father
        return g

###############################################################################

# reading command-line arguments
inpath, outpath = sys.argv[1:3]

# reading GEDCOM file into graph
g = TheGraph.read_from_gedcom(inpath)

# filtering out the main line of inheritance
gmain = GraphView(g, efilt=g.ep.main)

# indexing connected components of the filtered graph
# as the genealogical branches of the tree
counter = Counter(g)
counts = {}
for v in g.vertices():
    if v.in_degree() == 0:
        dfs_search(gmain, v, counter)
        if counter.count > 1:
            counts[v] = counter.count

# sorting the branches by the size in descending order
roots = []
num_from_root = {}
for v in sorted(counts, key=counts.get, reverse=True):
    roots.append(v)
    num_from_root[v] = str(len(roots))

# writing results as HTML
with open(outpath, 'wt') as f:
    f.write('''<!DOCTYPE html>
<head><meta charset="utf-8" />
<style type="text/css"><!--
  body {font-family:'DejaVu Serif', serif;}
  .dates {font-size:smaller;}
  .diagrams {font-weight:bold;}
  .invis {visibility:hidden;}
--></style></head><body>
''')
    for v in roots:
        f.write('<h2>Diagram %s. %s</h2>\n' % (num_from_root[v], g.vp.surn[v]))
        printer = Printer(g, counter.roots_per_vertex, num_from_root)
        dfs_search(gmain, v, printer)
        f.write('<p>\n')
        for line in printer.lines:
            f.write(line+"<br>\n")
        f.write('</p>\n')
    f.write('</body>\n</html>\n')
