# ged2html

This simple program generates a set of human-readable & printable hierarchical HTML diagrams from the genealogical data in GEDCOM format.

Genealogical data (family trees) can rarely be represented in the hierarchical (“tree-ish”) way. If we start from any given individual and represent their ancestors in a form of a tree, we cannot easily visualize other relatives (cousins). Similarly, if we try to represent descendants in a hierarchical way, we cannot visualize lineage of spouses. Also, the genealogical trees of medium and large sizes become more and more complicated due to independent ancestors of a given individual often being related to each other.

This program tackles this problem by dividing genealogical data into separate lineages, interconnected with each other, where each lineage can be represented in a hierarchical way and is represented with a Unicode-rich HTML diagram, ready for printing.

## Usage

```
usage: ged2html.py [-h] [--out OUT] [--pagedir PAGEDIR] input.ged [start_id]
```

### Examples

Example genealogical data is available in the `example` subdirectory. File `royal92.ged` is a “classic” dataset by Denis Reid from 1992. To visualize the entire data, we write

```
./ged2html.py --out=output.html example/royal92.ged
```

which generates a single file `output.html` with 215 (!) separate diagrams, starting like this:

![all.png](/example/all.png?raw=true)

To limit the amount of generated data, we can choose any one individual and restrict the output to individuals related to the selected person. For example, to generate diagrams for the ancestors, descendants and cousins of Princess Diana, we write

```
./ged2html.py --out=output.html example/royal92.ged I65
```

which results in *only* 16 diagrams, with the largest one looking like this:

![diana.png](/example/diana.png?raw=true)

By analysing the connections between diagrams, we can notice the significant mixing between separate lineages, even for such a small subset of our data.

### Separate pages

Specifying `--pagedir` instead of, or in addition to, `--out` will generate interlinked, separate HTML pages with extremely simple layout, one for each individual.

For example, requesting

```
./ged2html.py --pagedir=test example/royal92.ged I65
```

will generate a set of HTML pages in the `test` directory. One of the files consisting of data of Prince Charles will be called `I58.html` and look like this:

![charles.png](/example/charles.png?raw=true)

These pages will _not_ be hyperlinked to the HTML diagram generated with `--out` option.