from collections import namedtuple
import os.path


class Node:
    is_node = True
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
class Entry:
    is_node = False

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
        
        prefix = os.path.commonprefix((key, entry_key))
        new_pos = len(prefix)

        k_byte = 0 if new_pos >= key_len else key[new_pos]
        e_byte = 0 if new_pos >= len(entry_key) else entry_key[new_pos]
        new_mask = k_byte ^ e_byte

        if new_mask == 0:
            raise AssertionError('what')
        
        while new_mask & (new_mask-1) != 0: # all but one bit is set
            new_mask = new_mask & (new_mask-1) # clear out lower order bit
        new_mask = new_mask ^ 255 # We use an inverted mask to make other things nicer.

        new_node = Node(new_pos, new_mask)
        new_entry = Entry(key, value)

        new_node.set(Entry(key, value))
            
        # Insert new Entry
        cursor = self.root
        prev_cursor = None
        while True:
            if not cursor.is_node:
                break
            if cursor.pos > new_pos:
                break
            if cursor.pos == key_len and cursor.mask > new_mask:
                # mask is inverted so if a > b then a's mask is for lower bit (longer prefix)
                break
            prev_cursor, cursor = cursor, cursor.get(key)

        if new_node.direction(key) == 1:
            new_node.zero_bit = cursor
        else:
            new_node.one_bit = cursor

        if prev_cursor is None:
            self.root = new_node
        else:
            prev_cursor.swap(cursor, new_node)
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

