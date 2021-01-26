#!/usr/bin/env python3

"""csvjoin.py: a CSV joiner.

Program runs through 2+ CSV input files.

First, it joins the files through a column from each file. For that, it runs
through the first file, and gets the value from its join column. At the
same time it runs through the second file, and checks whether it can find
the same value in the second file's join column. If it cannot, it goes to
the next line in the first file. If it does, it keeps doing so until it
reaches the last file.

For every match (where there is a line on each of the N files whose column
contains the same value), it outputs a set of columns, defined from the
input ones using the syntax "`op(<i>:<colname>)`", where "`<i>`" is the
input file number (counting from 0), "`<colname>`" is the column name
(or number) affects, and `op()` is a generic python string that produces
a value.

Note that columns can be expressed using the column number, or the column
name (assuming the first line in csv file contains "# colname1, colname2,
...").


So, for example, to join 2 CSV files that contain the same value in the
"`city`" column, and output one column from each file, and the sum of 2
colums, we would use:

```
# ./csvjoin.py -i file0.csv -i file1.csv --join 0:city 1:city -o out.csv \
    --out-col 0:city --out-col 1:bar --out-col "0:foo + 1:bar"
```

"""

import argparse
import functools
import re
import sys


__version__ = '0.1'

YSCALE_VALUES = ('linear', 'log', 'symlog', 'logit')

default_values = {
    'debug': 0,
    'sep': ',',
    'join': None,
    'out_cols': [],
    'infile': [],
    'outfile': None,
}


COLUMN_NAME_RE = r'\d+\:[\w\d_]+'


def is_column_name(colname):
    # ensure end-to-end match
    column_name_re = r'^%s$' % COLUMN_NAME_RE
    return re.match(column_name_re, colname) is not None


def parse_column_name(colname, colnames_list):
    i, field = colname.split(':')
    i = int(i)
    return i, colnames_list[i].index(field)


class Expression(object):

    def __init__(self, colname, colnames_list):
        if is_column_name(colname):
            # column cointains a simple value
            self.expr_ = ''
            try:
                self.pars_ = parse_column_name(colname, colnames_list)
            except ValueError:
                raise Exception('error: unknown column name (%s)' % colname)
        else:
            # column cointains an expression
            self.pars_ = []
            pos_list = []
            for match in re.finditer(COLUMN_NAME_RE, colname):
                # store the positions
                pos_list.append(match.span())
                # parse the column name
                try:
                    self.pars_.append(parse_column_name(match.group(),
                                                        colnames_list))
                except ValueError:
                    raise Exception('error: unknown column name (%s)' %
                                    match.group())
            # fix the positions
            for (i, j) in reversed(pos_list):
                colname = colname[:i] + '{}' + colname[j:]
            self.expr_ = colname

    def run(self, lines):
        if not self.expr_:
            # return the simple value
            return lines[self.pars_[0]][self.pars_[1]]
        else:
            vals = ((lines[i][j]) for i, j in self.pars_)
            # eval the value
            return str(eval(self.expr_.format(*vals)))


def read_data(infile):
    # open infile
    if infile == '-':
        infile = '/dev/fd/0'
    with open(infile, 'r') as fin:
        # read data
        raw_data = fin.read()
    return raw_data


def parse_csv(raw_data, sep):
    # split the input in lines
    lines = raw_data.split('\n')
    # look for named columns in line 0
    column_names = []
    if lines[0].strip().startswith('#'):
        column_names = lines[0].strip()[1:].strip().split(sep)
        # remove spaces
        column_names = [colname.strip() for colname in column_names]
    # remove comment lines
    lines = [line.split(sep) for line in lines if line and
             not line.strip().startswith('#')]
    # strip spaces from items
    lines = [[item.strip() for item in line] for line in lines]
    return column_names, lines


def get_field_list(infile_list, join_list, colnames_list):
    # check the length of the join fields is equal to the number of input files
    numfiles = len(infile_list)
    assert numfiles == len(join_list), (
        'join list must contain 1 entry per input files (%i) -- instead it '
        'contains %i' % (numfiles, len(join_list)))

    # get the list of join fields
    join_columns = {}
    for join in join_list:
        try:
            i, join_columns[i] = parse_column_name(join, colnames_list)
        except ValueError:
            raise Exception('error: unknown column name (%s)' % join)

    # make sure they field keys cover the input file range
    assert set(range(numfiles)) == {k for k, v in join_columns.items()}, (
        'join list must contain entries for each of the input files '
        '(%r != %r)' % (set(range(numfiles)),
                        {k for k, v in join_columns.items()}))

    # deco-sort the join fields dictionary by the keys
    item_list = list(join_columns.items())
    item_list.sort()
    field_list = [field for _, field in item_list]

    return field_list


# the mechanism to match columns for N sources works as follows: We have
# a counter for each of the sources, which we init at zero. Then, we loop
# through all the rows of the first source. For each of the rows, we
# check whether there is a match in all the remaining N-1 sources.
# * if there is no match for all of them, we try with the next row of
#   the first source (but do not move the remaining N-1 counters)
# * if there is a match for all of them, add a new match to the match
#   list, and move all the counters to the next element
def get_match_list(lines_list, join_field_list):
    # create counters for each file
    ii = [0] * len(lines_list)
    match_list = []

    def no_finished_list(ii, lines_list):
        return functools.reduce(
            bool.__and__,
            [(ii[i] < len(lines_list[i])) for i in range(len(ii))])

    while no_finished_list(ii, lines_list):
        match = []
        # get the join value from the first file
        i = 0
        join_value = lines_list[i][ii[i]][join_field_list[i]]
        match.append(ii[i])
        # check for it in all the other files
        match_found = True
        for i in range(1, len(lines_list)):
            for j in range(ii[i], len(lines_list[i])):
                jv = lines_list[i][j][join_field_list[i]]
                if jv == join_value:
                    match.append(j)
                    break
            else:
                # column does not match:
                match_found = False
                break
        if not match_found:
            ii[0] += 1
            continue
        # match
        match_list.append(match)
        # update counters
        ii = match
        ii = [i+1 for i in ii]
    return match_list


def get_options(argv):
    # parse opts
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-d', '--debug', action='count',
                        dest='debug', default=default_values['debug'],
                        help='Increase verbosity (multiple times for more)',)
    parser.add_argument('--quiet', action='store_const',
                        dest='debug', const=-1,
                        help='Zero verbosity',)
    parser.add_argument('--sep', action='store', type=str,
                        dest='sep', default=default_values['sep'],
                        metavar='SEP',
                        help='use SEP as separator',)
    parser.add_argument('--join', action='store', type=str, nargs='+',
                        dest='join', default=default_values['join'],
                        metavar='JOIN',
                        help='use JOIN as join field list',)
    parser.add_argument('--out-col', action='append',
                        dest='out_cols', default=default_values['out_cols'],
                        metavar='out-col',
                        help='output column(s)',)
    parser.add_argument('-i', '--infile', action='append',
                        default=default_values['infile'],
                        metavar='input-file',
                        help='input file(s)',)
    parser.add_argument('-o', type=str,
                        dest='outfile', default=default_values['outfile'],
                        metavar='output-file',
                        help='output file',)
    # do the parsing
    options = parser.parse_args(argv[1:])
    return options


def main(argv):
    # parse options
    options = get_options(argv)

    # get infile(s)/outfile
    if options.outfile == '-':
        options.outfile = '/dev/fd/1'

    # print results
    if options.debug > 0:
        print(options)

    # read all the input fields
    # TODO(chema): there should be a less memory-constrained way to do this
    colnames_list = []
    lines_list = []
    for infile in options.infile:
        colnames, lines = parse_csv(read_data(infile), options.sep)
        colnames_list.append(colnames)
        lines_list.append(lines)

    # get a sorted field list for the join
    join_field_list = get_field_list(options.infile, options.join,
                                     colnames_list)

    # get a list of matches
    match_list = get_match_list(lines_list, join_field_list)

    # pre-process the output columns
    expr_list = []
    for colname in options.out_cols:
        expr_list.append(Expression(colname, colnames_list))

    # open outfile
    with open(options.outfile, 'w') as fout:
        # run all the matches
        for row_list in match_list:
            lines = list(l[i] for i, l in zip(row_list, lines_list))
            out_cols = [expr.run(lines) for expr in expr_list]
            fout.write(','.join(out_cols) + '\n')


if __name__ == '__main__':
    # at least the CLI program name: (CLI) execution
    main(sys.argv)
