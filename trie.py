from collections import namedtuple

import os.path
import random


class Tree:
    def __init__(self):
        self.root = None

    def count(self):
        if self.root is None:
            return 0
        return self.root.count()

    def lookup(self, key):
        if self.root is None:
            return

        key = key.encode('utf-8') if not isinstance(key, bytes) else key
        entry = self.root.walk(key)

        if entry.key == key:
            return entry.value

    def prefix_find(self, prefix):
        if self.root is None:
            return ()

        prefix = prefix.encode('utf-8') if not isinstance(prefix, bytes) else prefix
        if prefix:
            top = self.root.find_top(prefix, None)
        else:
            top = self.root

        if top is None:
            return ()

        entry = top.walk(prefix)

        if entry.key.startswith(prefix):
            return top.traverse()

    def random_walk(self, rng):
        if self.root is None:
            return None

        return self.root.random_walk(rng)

    def insert(self, key, value):
        key = key.encode('utf-8') if not isinstance(key, bytes) else key
        key_len = len(key)

        if self.root is None:
            self.root = Entry(key, value)
            return self.root

        entry = self.root.walk(key)
        entry_key = entry.key

        if key == entry_key:
            return entry

        new_entry = Entry(key, value)
        new_node = Node.from_smallest_prefix_of(key, entry_key)

        if new_node.direction(new_entry.key) == 1:
            new_node.one_bit = new_entry
            new_node.n_one = 1
        else:
            new_node.zero_bit = new_entry
            new_node.n_zero = 1

        self.root = self.root.insert(key, new_node)

        if new_node.zero_bit is None or new_node.one_bit is None:
            raise AssertionError("incomplete tree built")

        return new_entry

    def delete(self, key):
        if self.root is None:
            return

        key = key.encode('utf-8') if not isinstance(key, bytes) else key
        self.root, entry = self.root.delete(key)
        return entry

    def __str__(self):
        return "<Tree {}>".format(self.root)

class Entry:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def count(self):
        return 1

    def walk(self, key):
        return self

    def random_walk(self, rng):
        return self

    def traverse(self):
        yield self

    def find_top(self, prefix, current_top):
        return current_top

    def insert(self, key, node):
        if node.direction(key) == 1:
            node.zero_bit = self
            node.n_zero = 1
        else:
            node.one_bit = self
            node.n_one = 1
        return node

    def delete(self, key):
        if key == self.key:
            return None, key
        else:
            return self, None

    def __str__(self):
        return "{}".format(self.key)

class Node:
    def __init__(self, pos, mask):
        self.pos = pos
        self.mask = mask
        self.zero_bit = None
        self.one_bit = None
        self.n_zero = 0
        self.n_one = 0

    def count(self):
        return self.n_zero+self.n_one

    def traverse(self):
        for x in self.zero_bit.traverse():
            yield x
        for y in self.one_bit.traverse():
            yield y

    def random_walk(self, rng):
        if rng.randrange(self.count()) < self.n_zero:
            return self.zero_bit.random_walk(rng)
        else:
            return self.one_bit.random_walk(rng)

    def direction(self, key):
        # Mask is 1101111 so if or'd we get ff if bit 5 is set
        # ff +1 >> 8 is 1, < ff is 0
        byte = key[self.pos] if self.pos < len(key) else 0
        return (1 + (self.mask | byte)) >> 8

    def get(self, key):
        if self.direction(key) == 1:
            return self.one_bit
        else:
            return self.zero_bit

    def walk(self, key):
        return self.get(key).walk(key)

    def find_top(self, key, current_top):
        if self.pos < len(key):
            top = self.get(key)
            return top.find_top(key, top)
        return current_top

    def insert(self, key, new_node):
        if (self.pos > new_node.pos) or \
           (self.pos == new_node.pos and self.mask > new_node.mask):
            # mask is inverted so if a > b then a's mask is for more specific prefix
            if new_node.direction(key) == 1:
                new_node.zero_bit = self
                new_node.n_zero = self.count()
            else:
                new_node.one_bit = self
                new_node.n_one = self.count()
            return new_node
        else:
            if self.direction(key) == 1:
                self.one_bit = self.one_bit.insert(key, new_node)
                self.n_one = self.one_bit.count()
            else:
                self.zero_bit = self.zero_bit.insert(key, new_node)
                self.n_zero = self.zero_bit.count()
            return self

    def delete(self, key):
        if self.direction(key) == 1:
            self.one_bit, entry = self.one_bit.delete(key)
            if self.one_bit is None:
                return self.zero_bit, entry
            self.n_one = self.one_bit.count()
        else:
            self.zero_bit, entry = self.zero_bit.delete(key)
            if self.zero_bit is None:
                return self.one_bit, entry
            self.n_zero = self.zero_bit.count()

        return self, entry

    def __str__(self):
        return "<Node {}:{:b} {}:{}>".format(self.pos, self.mask ^255, self.zero_bit, self.one_bit)

    @classmethod
    def from_smallest_prefix_of(cls, key_a, key_b):
        prefix = os.path.commonprefix((key_a, key_b))
        new_pos = len(prefix)

        a_byte = 0 if new_pos >= len(key_a) else key_a[new_pos]
        b_byte = 0 if new_pos >= len(key_b) else key_b[new_pos]
        new_mask = b_byte ^ a_byte

        if new_mask == 0:
            raise AssertionError('what')

        while new_mask & (new_mask-1) != 0: # all but one bit is set
            new_mask = new_mask & (new_mask-1) # clear out lower order bit
        new_mask = new_mask ^ 255 # We use an inverted mask to make other things nicer.

        return cls(new_pos, new_mask)


if __name__ == '__main__':
    t = Tree()
    for i,k in enumerate([b"abc", b"abcd", b"bbcd",b"aaaaaaaa",b"AAAA",b"ACCC",b"AzzzZZZ"]):
        print("insert {} {}, count {}".format(k,t.insert(k,i), t.count()))
    for k in [b"abc", b"abcd", b"bbcd", b"xxx", b"",b"sjsjjsjsjsjsjjs"]:
        print("lookup {} {}".format(k,t.lookup(k)))
    for k in [b"abc", b"abcd", b"bbcd", b"xxx",b"",b"sjsjjsjsjsjsjjs"]:
        print("delete {} {}, count {}".format(k, t.delete(k), t.count()))
    for k in [b"abc", b"abcd", b"bbcd"]:
        print("lookup {} {}".format(k,t.lookup(k)))
    for k in t.prefix_find(b"A"):
        print("prefix A {}".format(k))
    for k in t.prefix_find(b""):
        print("prefix '' {}".format(k))
