import hashlib
from uuid import uuid4 as uuid
import sys
import zlib
import struct
import time
import random
from collections import Counter, namedtuple
from statistics import mean, stdev
import trie

def _make_hash(h):
    def _hash(*buffer):
        m=h()
        for b in buffer:
            m.update(b)

        return int(m.hexdigest(), 16)
    return _hash

md5 = _make_hash(hashlib.md5)

def _make_bhash(h):
    def _hash(*buffer):
        m=h()
        for b in buffer:
            m.update(b)

        return m.digest()
    return _hash

md5b = _make_bhash(hashlib.md5)
def djbhash(*m):
    h = 5381
    for a in m:
        for b in a:
            h = (((h << 5) + h) + b) & 4294967295 
    return h

def timer():
    t = time.time()
    def _timer():
        return time.time() - t
    return _timer


def bsearch(key, workers):
    # find smallest worker larger than the key
    lo, hi = 0, len(workers)
    best = 0
    while lo < hi:
        mid = (hi+lo)//2
        pivot = workers[mid]
        # 0 , 1 , 2, 3, 4, 5
        #print(lo, hi, mid, key, pivot)
        if pivot < key:
            lo, hi = mid+1, hi
        else:
            lo, hi = lo, mid
            best = mid
    return best

def consistent_hash(hash, nvnodes):
    def chooser(workers):
        vnodes = [uuid().bytes for _ in range(nvnodes)]
        worker_hashes = sorted((hash(n, w),w) for w in workers for n in vnodes)
        hashes, workers = zip(*worker_hashes)

        def find(message):
            h = hash(message)
            o = bsearch(h, hashes)
            return workers[o]
        return find
    return chooser

def trie_chooser(hash):
    def chooser(workers):
        t = trie.Tree()
        for w in workers:
            t.insert(hash(w), w)
        def find(message):
            r = random.Random(message)
            return t.random_walk(r)
        return find
    return chooser

def rendevous_hash(hash):
    def chooser(workers):
        def find(m):
            worker_hashes = [(hash(m, w), w) for w in workers]
            min_worker = min(worker_hashes, key=lambda x:x[0])
            return min_worker[1]
        return find
    return chooser
            
def perfect_shuffle_djb():
    def chooser(workers):
        def find(m):
            h = 5381
            for b in m:
                h = (((h << 5) + h) + b)
            h = h & 4294967295 
            worker_choice = []
            for c,w in enumerate(workers):
                pos = (h >> 13)  % (c+1)
                h = (((h << 5) + h) + pos) & 4294967295 
                if pos != c:
                    worker_choice.append(worker_choice[pos])
                    worker_choice[pos] = w 
                else:
                    worker_choice.append(w)

            return worker_choice[0]
        return find
    return chooser





    
    
if __name__ == '__main__':
    nworkers, nmessages = int(sys.argv[1]), int(sys.argv[2])
    workers = [uuid().bytes for n in range(nworkers)]
    random.shuffle(workers)

    messages = [uuid().bytes for n in range(nmessages)]

    tests = [
        ("consistent hashing (md5) 256 vnodes", consistent_hash(md5, nvnodes=250)),
        ("trie choosing ", trie_chooser(md5b)),
        ("perfect shuffle (djbhash)", perfect_shuffle_djb()),
        #("rendevouz hashing (md5)", rendevous_hash(md5)),
    ]
    print ("setup done")
    runs = []
    for name, make_chooser in tests:
        counter = Counter({w:0 for w in workers})
        choose_server = make_chooser(workers)
        t=timer()
        for m in messages:
            counter[choose_server(m)]+=1
        t=t()
        runs.append((name, counter, t))

    print()

    runs.sort(key=lambda x:x[2])

    for name, counter, t in runs:
        counts = counter.values()
        m = nmessages/nworkers
        max_,min_ = max(counts), min(counts)
        print("{:<20} 1 message ~{:.8f}ms, balance ({},{}) {:<5.0%}".format(
           name,t*1000/nmessages, min_, max_, min_/max_))


