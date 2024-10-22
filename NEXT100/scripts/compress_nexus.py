import sys
import tables as tb

filename_in  = sys.argv[1]
filename_out = sys.argv[2]

compression = tb.Filters(complib="zlib", complevel=4)

with tb.open_file(filename_out, mode="w", filters=compression) as file_out:
    with tb.open_file(filename_in) as file_in:
         file_out.copy_node(file_in.root.MC, file_out.root, recursive=True, filters=compression)