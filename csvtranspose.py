#!/usr/bin/env python3

"""csvtranspose.py: a CSV transposer.

Program transposes rows and columns on CSV files.

Example:
```
# ./csvtranspose.py in.csv out.csv
```

"""

import argparse
import csv
import sys


__version__ = "0.1"

default_values = {
    "debug": 0,
    "infile": None,
    "outfile": None,
}


def get_options(argv):
    # parse opts
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-d",
        "--debug",
        action="count",
        dest="debug",
        default=default_values["debug"],
        help="Increase verbosity (multiple times for more)",
    )
    parser.add_argument(
        "--quiet",
        action="store_const",
        dest="debug",
        const=-1,
        help="Zero verbosity",
    )
    parser.add_argument(
        "infile",
        type=str,
        default=default_values["infile"],
        metavar="input-file",
        help="input file",
    )
    parser.add_argument(
        "outfile",
        type=str,
        default=default_values["outfile"],
        metavar="output-file",
        help="output file",
    )
    # do the parsing
    options = parser.parse_args(argv[1:])
    return options


def main(argv):
    # parse options
    options = get_options(argv)

    # get infile/outfile
    if options.infile == "-":
        options.infile = "/dev/fd/0"
    if options.outfile == "-":
        options.outfile = "/dev/fd/1"

    # print results
    if options.debug > 0:
        print(options)

    # read the input
    with open(options.infile, "r") as fin:
        input_data = csv.reader(fin.read().splitlines())

    # rotate it
    output_data = zip(*input_data)

    # write it as output
    out_writer = csv.writer(open(options.outfile, "w"))
    out_writer.writerows(output_data)


if __name__ == "__main__":
    # at least the CLI program name: (CLI) execution
    main(sys.argv)
