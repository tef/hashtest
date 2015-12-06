from collections import namedtuple
import os.path


class Node:
    def __init__(self, pos, mask):
        self.pos = pos
        self.mask = mask
        self.zero_bit = None
        self.one_bit = None
        self.parent = None

    def direction(self, key):
        byte = key[self.pos] if self.pos < len(key) else 0
        # Mask is 1101111 so if or'd we get ff if bit 5 is set
        # ff +1 >> 8 is 1, < ff is 0
        return (1 + (self.mask | byte)) >> 8

    def set(self, entry):
        if self.direction(entry.key) == 1:
            self.one_bit = entry
        else:
            self.zero_bit = entry
        entry.parent = self
    
    def swap(self, old, new):
        if self.one_bit == old:
            self.one_bit = new
        else:
            self.zero_bit = new

    def get(self, key):
        if self.direction(key) == 1:
            return self.one_bit
        else:
            return self.zero_bit

    def walk(self, key):
        return self.get(key).walk(key)

    def delete(self, key):
        if self.direction(key) == 1:
            self.one_bit, entry = self.one_bit.delete(key)
            if self.one_bit is None:
                return self.zero_bit, entry

        else:
            self.zero_bit, entry = self.zero_bit.delete(key)
            if self.zero_bit is None:
                return self.one_bit, entry

        return self, entry

            
    def insert(self, key, new_node):
        # case: 
            # i am root, and too fine
            # so should return new_node
        if self.finer_than(new_node):
            if self.direction(key) == 1:
                new_node.zero_bit = self
            else:
                new_node.one_bit = self
            return new_node
        else:
            if self.direction(key) == 1:
                self.one_bit = self.one_bit.insert(key, new_node)
            else:
                self.zero_but = self.zero_but.insert(key, new_node)
            return self


    def finer_than(self, node):
        return (self.pos > node.pos) or \
               (self.pos == node.pos and cursor.mask > node.mask)
        # mask is inverted so if a > b then a's mask is for lower bit (longer prefix)

    @classmethod
    def between(cls, key_a, key_b):
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
        
class Entry:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.left = None
        self.right = None

    def walk(self, key):
        return self

    def delete(self, key):
        if key == self.key:
            return None, key
        else:
            return self, None

    def insert(self, key, node):
        node.set(self)
        return node

    def finer_than(self, node):
        return True

    def __str__(self):
        return "<Entry {}:{}>".format(self.key, self.value)

class Tree:
    def __init__(self):
        self.root = None

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
        new_node = Node.between(key, entry_key)

        new_node.set(new_entry)

        self.root = self.root.insert(key, new_node)

        return new_entry

    def lookup(self, key):
        if self.root is None:
            return

        key = key.encode('utf-8') if not isinstance(key, bytes) else key
        entry = self.root.walk(key)

        if entry and entry.key == key:
            return entry.value

    def delete(self, key):
        if self.root is None:
            return 
        key = key.encode('utf-8') if not isinstance(key, bytes) else key
        self.root, entry = self.root.delete(key)
        return entry


if __name__ == '__main__':
    t = Tree()
    for i,k in enumerate(["abc", "abcd", "bbcd"]):
        print("lookup {} {}".format(k,t.insert(k,i)))
    for k in ["abc", "abcd", "bbcd", "xxx", "","sjsjjsjsjsjsjjs"]:
        print("lookup {} {}".format(k,t.lookup(k)))
    for k in ["abc", "abcd", "bbcd", "xxx", "","sjsjjsjsjsjsjjs"]:
        print("delete{} {}".format(k, t.delete(k)))
    for k in ["abc", "abcd", "bbcd"]:
        print("lookup {} {}".format(k,t.lookup(k)))

