import clang
import os
clang.cindex.Config.set_library_path(os.environ['CLANG_LIBRARY_PATH'])
