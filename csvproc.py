#!/usr/bin/env python3

"""csvproc.py module description."""


import ast
import argparse
import operator
import pandas as pd
import re
import sys


default_values = {
    "debug": 0,
    "header": True,
    "add_column": None,
    "equation": None,
    "infile": None,
    "outfile": None,
}


# Dictionary of supported operators
operators = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.BitXor: operator.xor,
}


def eval_expr(expr, variables):
    """
    Evaluate a mathematical expression with given variables.

    :param expr: The expression to evaluate (as a string).
    :param variables: A dictionary of variable values.
    :return: The result of the evaluated expression.
    """

    # parse the expression into an AST
    node = ast.parse(expr, mode="eval").body

    def _eval(node):
        if isinstance(node, ast.Constant):  # <number>
            return node.value
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            left = _eval(node.left)
            right = _eval(node.right)
            return operators[type(node.op)](left, right)
        elif isinstance(node, ast.Name):
            return variables[node.id]
        else:
            raise TypeError(node)

    return _eval(node)


def add_column(infile, column_name, equation, outfile, header):
    # read csv
    df = pd.read_csv(infile, header=0 if header else None)

    # parse equation
    assert equation is not None, "error: need a valid equation"

    # look for variables referring to column numbers ("$<n>$) and
    # replace them with "column_<n>".
    def replacer(match):
        index = int(match.group(1)) - 1
        return f"column_{match.groups()[0]}"

    equation = re.sub(r"\$(\d+)", replacer, equation)
    num_cols = df.shape[1]
    # create a new column
    for tup in df.itertuples():
        variables = tup._asdict()
        for i in range(num_cols + 1):
            variables[f"column_{i}"] = tup[i]
        new_value = eval_expr(equation, variables)
        index = tup[0]
        df.loc[index, column_name] = new_value
    # write csv
    df.to_csv(outfile, header=header, index=False)


def get_options(argv):
    """Generic option parser.

    Args:
        argv: list containing arguments

    Returns:
        Namespace - An argparse.ArgumentParser-generated option object
    """
    # init parser
    # usage = 'usage: %prog [options] arg1 arg2'
    # parser = argparse.OptionParser(usage=usage)
    # parser.print_help() to get argparse.usage (large help)
    # parser.print_usage() to get argparse.usage (just usage line)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-d",
        "--debug",
        action="count",
        dest="debug",
        default=default_values["debug"],
        help="Increase verbosity (use multiple times for more)",
    )
    parser.add_argument(
        "--quiet",
        action="store_const",
        dest="debug",
        const=-1,
        help="Zero verbosity",
    )
    parser.add_argument(
        "--header",
        action="store_const",
        const=True,
        dest="header",
        default=default_values["header"],
        help="Read CSV header from first row (even if no #)",
    )
    parser.add_argument(
        "--no-header",
        action="store_const",
        const=False,
        dest="header",
        default=default_values["header"],
        help="Do not read CSV header from first row (even if no #)",
    )
    parser.add_argument(
        "--add-column",
        action="store",
        dest="add_column",
        default=default_values["add_column"],
        metavar="COLUMN_NAME",
        help="use COLUMN_NAME for add_column",
    )
    parser.add_argument(
        "-e",
        "--equation",
        action="store",
        dest="equation",
        default=default_values["equation"],
        metavar="EQUATION",
        help="use EQUATION equation",
    )
    parser.add_argument(
        "-i",
        "--infile",
        dest="infile",
        type=str,
        default=default_values["infile"],
        metavar="input-file",
        help="input file",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        dest="outfile",
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
    # get infile
    if options.infile is None or options.infile == "-":
        options.infile = "/dev/fd/0"
    if options.outfile is None or options.outfile == "-":
        options.outfile = "/dev/fd/1"
    # print results
    if options.debug > 0:
        print(options)
    # do something
    add_column(
        options.infile,
        options.add_column,
        options.equation,
        options.outfile,
        options.header,
    )


if __name__ == "__main__":
    # at least the CLI program name: (CLI) execution
    main(sys.argv)
