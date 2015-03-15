#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------
# Copyright (c) 2015 Michelle Baert
# Some rights reserved
# file: {} created by mich on 15/03/15.
# ----------------------------------------
"""
A great python script

"""
import logging
import os

logging.basicConfig(level='DEBUG')
logger = logging.getLogger()
import re


class Xref(object):
    """
    >>> m = Xref.pat_imp_names.match('from   ext import   db, manager')
    >>> m and (m.groups(), m.group(2).split(','))
    (('ext', '  db, manager'), ['  db', ' manager'])
    >>> m = Xref.pat_imp_mods.match('import models, views')
    >>> m and m.groups()
    ('models, views',)
    """
    pat_comment = re.compile('^(.*?)#(.*)')
    pat_imp_names = re.compile('from +(\S+) +import (.*)')
    pat_imp_mods = re.compile('import (.*)')

    def __init__(self, approot):
        self.dot_src = None
        self.packages = []
        self.approot = approot
        self.xref = {}

    @classmethod
    def read_imports(cls, filename):
        """
        TODO package import
        """
        logger.debug("Parsing %s",  filename)
        with open(filename) as f:
            rslts = []
            for line in f:
                # remove eoln and comments
                stmt = line.strip()
                m = cls.pat_comment.match(stmt)
                if m:
                    stmt = m.group(1)
                # imports by name
                m = cls.pat_imp_names.match(stmt)
                if m:
                    logger.debug("  - IN %s", line)
                    rslts.append( (m.group(1), [s.strip() for s in m.group(2).split(',')],))
                else:
                    # imports by module
                    m = cls.pat_imp_mods.match(stmt)
                    if m:
                        logger.debug("  - IM %s", line)
                        rslts += [(s.strip(),'.') for s in m.group(1).split(',')]
        logger.debug(rslts)
        return rslts

    def load(self, basedir=None):
        """
        Simple, non-recursive version
        """
        if not basedir:
            basedir = self.approot
        for f in os.listdir(basedir):
            if f[-3:] == '.py':
                mod = f[:-3]
                filename = os.path.join(basedir, f)
                self.xref[mod] = self.read_imports(filename)
        return self.xref

    def load_tree(self):
        """
        TODO walk into directory tree
        """
        cwd = os.getcwd()
        os.chdir(self.approot)
        my_ignore_dirs = ('.git', 'drafts')  # see also : glob standard module

        # I'm using os.walk which takes care of the recursion
        for root, dirs, files in os.walk('.', topdown=True):
            cur_package = '.'.join(root.split(os.sep)[1:])
            cur_modules = []
            logger.debug("Walking in package %r (%s)", cur_package, root)
            for f in files:
                if f[-3:]=='.py':
                    filename = os.path.join(root, f)

                    mod = f[:-3]
                    if cur_package:
                        mod = '.'.join((cur_package, mod))

                    logger.info("  module: %s (%s)", mod, filename)
                    imports = self.read_imports(filename)
                    cur_modules.append(mod)
                    self.xref[mod] = imports
            self.packages.append((cur_package, cur_modules))

            to_remove = []; dcnt = len(dirs)
            # removing dirs cannot be done in loop or we'd get strange behaviors
            for d in dirs:
                if d.find('draft') >= 0: # investigating some bug
                    logger.debug(" Testing dir: %s in %s"%(d,root))

                if d in my_ignore_dirs:
                    logger.info("  Ignoring: %s", d)
                    to_remove.append(d)
                else:
                    # package?
                    if os.path.exists(os.path.join(root,d, '__init__.py')):
                        logger.info("   package %s", os.path.join(root,d))
                    else:
                        logger.info("  Non-package %s: ", d)
                        #print "  Non-package: ", d
                        to_remove.append(d)

            for d in to_remove:
                dirs.remove(d)
            logger.debug("%d dirs processed, %d removed", dcnt, len(to_remove))
        os.chdir(cwd)
        return self.xref

    def to_dot(self):
        assert self.xref
        if self.dot_src:
            return self.dot_src
        
        dot_src= """digraph G {
        node [style="filled"];
        edge [fontsize="8",fontname="Arial"];

        """
        for package, modules in self.packages:
            if package:
                dot_src += '''subgraph "cluster_%s" {
                label="%s";
                color="navajowhite";
                style="filled";
                '''%(package, package.upper())
            for mod in modules:
                dot_src += '"%s" [label="%s"];\n'%(mod, mod.split('.')[-1])
                dot_src += ""
            if package:
                dot_src += "}\n"
        for dest, imports in self.xref.iteritems():
            for src, names in imports:
                # ignoring library (i.e. unknown) imports
                if src in self.xref:
                    dot_src += '    "{0}" -> "{1}" [label="{2}"];\n'.format(src, dest, ', '.join(names))
        dot_src += "}\n"
        self.dot_src = dot_src
        return dot_src

    def to_svg(self):
        dot_src = self.to_dot()
        return rundot(dot_src, 'svg')

    def to_png(self):
        dot_src = self.to_dot()
        return rundot(dot_src, 'png')

def rundot(s, fmt='svg'):
    """
    Execute dot and return a raw SVG image, or None.

    Borrowed from Chris Drakes's gvmagic.py https://github.com/cjdrake/ipython-magic
    """
    from subprocess import Popen, PIPE
    dot = Popen(['dot', '-T'+fmt], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdoutdata, stderrdata = dot.communicate(s.encode('utf-8'))
    status = dot.wait()
    if status == 0:
        return stdoutdata
    else:
        fstr = "dot returned {}\n[==== stderr ====]\n{}"
        raise Exception(fstr.format(status, stderrdata.decode('utf-8')))

def run(args):
    """

    >>> import argparse
    >>> run(argparse.Namespace(project_root='/tmp/flask-skeleton', log=None, svg=None, png=None, dot=None))
    digraph G {
            node [style="filled"];
            edge [fontsize="8",fontname="Arial"];
    <BLANKLINE>
            "run" [label="run"];
    "main" [label="main"];
    "config" [label="config"];
    "models" [label="models"];
        "main" -> "models" [label="db"];
        "models" -> "main" [label="."];
        "main" -> "run" [label="create_app, db, manager"];
        "models" -> "run" [label="."];
    }
    <BLANKLINE>
    """
    #logger.setLevel(logging.DEBUG)
    if args.log:
        logger.setLevel(args.log) # string is accepted as well as int
    logger.info("Running with %r", args)

    xref = Xref(args.project_root)
    xref.load_tree()

    if args.svg:
        with open(args.svg,'w') as f:
            f.write(xref.to_svg())

    if args.png:
        with open(args.png,'w') as f:
            f.write(xref.to_png())

    if args.dot:
        with open(args.dot,'w') as f:
            f.write(xref.to_dot())
    else:
        print xref.to_dot()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.description="Short description"
    parser.add_argument('-l','--log', metavar='LEVEL')#, default='WARNING')
    parser.add_argument('--svg')
    parser.add_argument('--png')
    parser.add_argument('--dot')
    parser.add_argument('project_root', help="root directory of your app")
    args = parser.parse_args()
    run(args)
