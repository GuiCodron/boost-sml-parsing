import clang

from clang.cindex import Cursor

class Action():
  def __init__(self, node: Cursor):
    self.node = node

  def to_string(self):
    pass
