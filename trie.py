"""A Critbit Tree for byte strings

A critbit trie is a bitwise prefix trie, with path compression - all 
nodes with one child are skipped. 

A critbit provides a dictionary of key-value pairs (entries):

>>> t = Tree()
>>> t.insert(b"aaa", 1)
<trie.Entry instance at 0x1029833f8>
>>> t.lookup(b"aaa")
1

but also provides traverse_prefix(prefix), and traverse() methods
which return generators of all Entries that match.

A critbit tree is a bunch of Nodes and Entities. Entities represent
the key-value pairs, and Nodes store a critical bit (as a byte position & byte mask)
, and two children (0 and 1).

the children of a node are ones which have the critical bit set to 1 (or 0), at that
position. 

This is based upon https://www.imperialviolet.org/binary/critbit.pdf, but
changed to not rely on \0 terminated strings, pointer aritmetic, assignment
to two-star pointers, iteration, flags for internal/external, or
the branch avoiding inverted bitmask. It's much less C but I do not know
how Python it is.
"""

from collections import namedtuple

import os.path
import random

class Tree:
    """ This is the wrapper class for the critbit trie, which manages building
    nodes, entities, and linking them together. 90% of this is empty tree handling"""

    def __init__(self):
        self.root = None

    def count(self):
        if self.root is None:
            return 0
        return self.root.count()

    class Node:
        """ Internal object, represents a critbit node, at a byte position,
        and a bitmask 
        """

        def __init__(self, pos, mask):
            self.pos = pos
            self.mask = mask
            self.child = [None, None]

        def count(self):
            return self.child[0].count() + self.child[1].count()

        def traverse(self):
            for x in self.child[0].traverse():
                yield x
            for y in self.child[1].traverse():
                yield y


        def direction(self, key):
            byte = key[self.pos] if self.pos < len(key) else 0
            return (self.mask & byte) == self.mask 

        def get(self, key):
            return self.child[self.direction(key)]

        def walk(self, key):
            """ Seek to the entity closest to the key in terms of critical bits shared,
            but it may not share a prefix """
            return self.get(key).walk(key)

        def first_greater_than(self, key):
            dir = self.direction(key)
            node = self.child[dir].first_greater_than(key)
            if dir == 0 and node is None:
                # we can be bigger
                node = self.child[1].first_greater_than(key)
            return node

        def find_top(self, prefix, current_top):
            """Find the top node that matches the prefix in terms of 
            critical bits shared, it may not share a prefix"""

            if self.pos < len(prefix):
                # keys are made of bytes, so if pos is under, mask fits too..
                top = self.get(prefix)
                # If the current node is at a position inside the prefix,
                # then one child will have a bit in common with the key
                # and therefore that child is a top candidate
                return top.find_top(prefix, top)
            # If we are beyond the current prefix,
            # whatever was passed in is the best candidate.
            return current_top

        def insert(self, key, new_node):
            """ This method is called on a node, and returns the new value for it
            in the node that contains it. By returning the new value, we 
            can swap in the new_node we want to insert, without having access
            to the parent node.
            """
            if (self.pos > new_node.pos) or \
               (self.pos == new_node.pos and self.mask < new_node.mask):
                # If the current node refers to a longer prefix than the new_node
                # It's the one we want to replace in the tree, so 
                # we move it inside of new_node into the empty child slot
                # and return new_node to update the parent.
                dir = new_node.direction(key)
                new_node.child[1-dir] = self
                return new_node
            else:
                # Either child will have a bit in common with the key,
                # so we deletgate to it and overwrite it, and return
                # self as we do not require the parent to change.
                dir = self.direction(key)
                self.child[dir] = self.child[dir].insert(key, new_node)
                return self

        def delete(self, key):
            """Delete a key from the tree, and return the current or a new node to
            replace this one in the parent node."""
            dir = self.direction(key)
            # Delegate to the child closest to the key
            self.child[dir], entry = self.child[dir].delete(key)
            # If it no longer exists, return the other child to replace
            # this object in the parent
            if self.child[dir] is None:
                return self.child[1-dir], entry
            # Otherwise, no change to parent.
            return self, entry

        def __str__(self):
            return "<Node {}:{:b} {}:{}>".format(self.pos, self.mask, self.child[0], self.child[1])

        def random_walk(self, rng):
            dir = rng.randrange(self.count()) >= self.child[0].count()
            return self.child[dir].random_walk(rng)

        @classmethod
        def from_smallest_prefix_of(cls, key_a, key_b):
            """ Given two keys (bytes), compute the smallest prefix,
            and thus the smallest critical bit. Store this bit as a byte position,
            and an mask. Return a new Node with pos and mask set, but
            empty child array"""

            # heh heh heh
            prefix = os.path.commonprefix((key_a, key_b))
            new_pos = len(prefix)

            # we null pad either key with 0's
            a_byte = 0 if new_pos >= len(key_a) else key_a[new_pos]
            b_byte = 0 if new_pos >= len(key_b) else key_b[new_pos]
            new_mask = b_byte ^ a_byte 

            # mask is all bits different, and at least one should be
            if new_mask == 0:
                raise AssertionError('what')

            # do bit tricks:
            # if x = 2, 4, 8, 16, 32, etc, x & (x-1) == 0
            # if x not power of 2, x &(x-1) clears bit but not leading bit.
            while new_mask & (new_mask-1) != 0: # all but one bit is set
                new_mask = new_mask & (new_mask-1) # clear out lower order bit

            return cls(new_pos, new_mask)

    class Entry:
        """A k-v pair"""
        def __init__(self, key, value):
            self.key = key
            self.value = value

        def count(self):
            return 1

        def walk(self, key):
            # Again, prefix(self.key) may not be prefix(key)   
            return self

        def traverse(self):
            yield self

        def first_greater_than(self, key):
            if self.key > key:
                return self

        def find_top(self, prefix, current_top):
            # We are the closest item to the prefix
            return current_top

        def insert(self, key, node):
            # We're inserting a node to replace us,
            # So find out where we put the new entry
            dir = node.direction(key)
            # and stick this entry in the other slot
            node.child[1-dir] = self
            return node

        def delete(self, key):
            if key == self.key:
                # Returning None here instructs the parent
                # that this entry is gone, and the parent
                # will in turn return the other child to replace it.
                return None, key
            else:
                # Otherwise, no changes
                return self, None

        def random_walk(self, rng):
            return self

        def __str__(self):
            return "{}".format(self.key)



    def lookup(self, key):
        if self.root is None:
            return

        key = key.encode('utf-8') if not isinstance(key, bytes) else key
        entry = self.root.walk(key)

        if entry.key == key: # check it actually matches.
            return entry.value

    def first_entry_greater_than(self, key, cyclic=False):
        if self.root is None:
            return

        key = key.encode('utf-8') if not isinstance(key, bytes) else key
        entry = self.root.first_greater_than(key)
        if entry is None and cyclic:
            entry = self.root.walk(b"")
        return entry

    def traverse(self):
        if self.root is None:
            return ()
        return self.root.traverse() # returning a generator. heh

    def traverse_prefix(self, prefix):
        if self.root is None:
            return ()

        prefix = prefix.encode('utf-8') if not isinstance(prefix, bytes) else prefix
        if prefix:
            top = self.root.find_top(prefix, None)
        else:
            top = self.root # use the root for empty prefix, as find_top
            # returns children of root.

        # top can be either a Node or an Entry
        # for an entry:
        # all parent nodes have a shorter pos than the length of the prefix.
        # so it is the only item in the tree that could match the prefix

        # if it is a node, then this node is the node where it's parent
        # had the highest pos shorter than the prefix length, and the node
        # itself's position will be higher than the prefix length.
        # therefore all children of this node share a common prefix
        # greater than the key, 

        # We walk to the first entry under top, and check the prefix
            
        entry = top.walk(prefix)
        if entry.key.startswith(prefix):
            return top.traverse() # return a generator

    def insert(self, key, value):
        key = key.encode('utf-8') if not isinstance(key, bytes) else key

        if self.root is None:
            self.root = self.Entry(key, value)
            return self.root

        # Find the closest entry to the key 
        entry = self.root.walk(key)
        if key == entry.key:
            return key
        
        # Build a new entry to insert
        new_entry = self.Entry(key, value)
        # and a node to hold it, using the smallest shared prefix
        # of the key and the key of the closest item
        new_node = self.Node.from_smallest_prefix_of(key, entry.key)

        # we stick our new entry in the matching child slot
        dir = new_node.direction(new_entry.key)
        new_node.child[dir] = new_entry

        # and ask the root to insert the new node, and return
        # the replacement root
        self.root = self.root.insert(key, new_node)
        # inside of this, it swaps new_node in

        # double check.
        if new_node.child[0] is None or new_node.child[1] is None:
            raise AssertionError("incomplete tree built")

        return key

    def delete(self, key):
        if self.root is None:
            return

        key = key.encode('utf-8') if not isinstance(key, bytes) else key
        # delegate to tree, returns new root and entry if found.
        self.root, entry = self.root.delete(key)
        return entry

    def random_walk(self, rng):
        if self.root is None:
            return None

        return self.root.random_walk(rng).value


    def __str__(self):
        return "<Tree {}>".format(self.root)


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
    for k in t.traverse_prefix(b"A"):
        print("prefix A {}".format(k))
    for k in t.traverse_prefix(b""):
        print("prefix '' {}".format(k))

    for k in [b"ABB", "AC","ACCC","AC","AD", "zz", "B"]:  
        print("first greater than {} is {}".format(k, t.first_entry_greater_than(k).key))
    print(t)

