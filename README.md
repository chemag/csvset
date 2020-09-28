# csvjoin: a CSV joiner

`csvjoin` is a CLI tool runs through 2+ CSV input files, joins them (using a column in each of the input files), and produces a new CSV file composed of elements of the input files, including operations on them. 


# Example

We have 2 files, named `file0.csv` and `file1.csv`, which contain

```
$ cat file0.csv 
# city, data, tmax, tmin, foo
Austin, 20140916, 111, 0, 1
Berkeley, 20140916, 222, 0, 2
Duke, 20140916, 444, 0, 3
Eaton, 20140916, 555, 0, 4

$ cat file1.csv 
# city, i1, i2, bar
Austin, 1, 11, 100
Berkeley, 2, 22, 200
Charleston, 3, 33, 300
Duke, 4, 44, 400
```

On these 2 files, we run the following command:

```
# ./csvjoin.py -i file0.csv -i file1.csv \
    --join 0:city 1:city \
    --out-col 0:city --out-col 1:bar --out-col "0:foo + 1:bar" \
    -o out.csv
```

We first provide the names of the input files (we need 2 or more), and the join fields, which in this case are `city` from the first file, and `city` from the second file.

Note that columns are expressed using the syntax "`<i>:<colname>`", where:
* "`<i>`" is the input file number (counting from 0),
* "`<colname>`" is the column name or number. This means we can refer to the "`data`" column in the first file as either `0:data` or `0:1`.

`csvjoin` will produce an internal join of both files based on the `city` column in both sides.

```
# 0:city, 0:data, 0:tmax, 0:tmin, 0:foo, 1:city, 1:i1, 1:i2, 1:bar
Austin, 20140916, 111, 0, 1 Austin, 1, 11, 100
Berkeley, 20140916, 222, 0, 2 Berkeley, 2, 22, 200
Duke, 20140916, 444, 0, 3 Duke, 4, 44, 400
```

Second, we provide a list of the output columns in the output file, and the output file itself (`out.csv`). Note that, for the output columns, we can either:
* cherry-pick columns from the input files (e.g. `--out-col 0:city` produces as the first column the contents of the `city` field of the first file, while `--out-col 1.bar` produces as the next column the contents of the `bar` field of the second file), or
* evaluate an expression containing references to multiple input columns. For example, in our case we want as the last column the reult of adding the contents of the `foo` column of the first file, and the `bar` column of the second file.

The final results will be:

```
$ cat out.csv 
Austin,100,101
Berkeley,200,202
Duke,400,403
```

# Join Operation Details

`csvjoin` joins the files through a column from each file.

For that, it runs through the first file, and gets the value from its join column. At the same time it runs through the second file, and checks whether it can find the same value in the second file's join column. If it cannot, it goes to the next line in the first file. If it does, it processes the third file. It keeps doing so until either there is no match in one of the files, or it reaches the last file.

For every match (where there is a line on each of the N files whose column contains the same value), it outputs a set of columns, defined from the input ones using the syntax "`op(<i>:<colname>)`", where "`<i>:<colname>`" represents a column (per the above syntax), and `op()` is a generic python string that produces a value.

We could also do:

```
$ ./csvjoin.py -i file0.csv -i file1.csv \
    --join 0:city 1:city 
    --out-col 0:city --out-col 1:bar --out-col "0:foo + 1:bar + 1000000" 
    -o out.csv

$ cat out.csv
Austin,100,1000101
Berkeley,200,1000202
Duke,400,1000403
```

# Requirements

Requires python3 with some packages.


# License

csvjoin is BSD licensed, as found in the [LICENSE](LICENSE) file.
