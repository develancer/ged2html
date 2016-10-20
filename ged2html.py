#!/usr/bin/python3
#####################################################################
# Convert GEDCOM family tree to a directed (sub)graph. Usage:
#   python gedcom2graph.py input.ged output.xml
#####################################################################
import sys
import re
import graph_tool

if sys.hexversion < 0x030000F0:
    sys.exit("ERROR: Python 3 is needed to run this program")

if len(sys.argv) < 3 :
    sys.exit("USAGE: gedcom2graph.py input.ged output.xml")


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

    def by_id(self, id: str):
        if id in self._vertex_by_id:
            v = self._vertex_by_id[id]
        else:
            v = self.add_vertex()
            self.vp.id[v] = id
            self._vertex_by_id[id] = v
        return v

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
            if ident == 'HUSB' or ident == 'WIFE':
                g.add_edge(g.by_id(other), g.by_id(lastid))
            if ident == 'CHIL' :
                g.add_edge(g.by_id(lastid), g.by_id(other))

g.save(outpath)
