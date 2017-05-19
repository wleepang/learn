#!/usr/bin/env python
"""
A script to explore parallelization via the multiprocessing package

Python :: 3
Python :: 3.6
"""

import os
import multiprocessing as mp
import time

def expensive(value, results=None, index=None):
    proc = mp.current_process()
    print('{}[{}]: working on index {} value {}'.format(proc.name, os.getpid(), index, value))
    time.sleep(2)

    result = value*2

    if results:
        results[index] = result
    else:
        return result


if __name__ == "__main__":
    # there are two basic methods for using multiple processes over an iterable 
    # list of data:
    # 1. spawning a process for each element in the list
    # 2. using a process pool to work on the data

    # for the most control, processes can be generated explicitly
    # with data communication handled as needed
    data = range(8)

    print('--- Example 1 ---')
    with mp.Manager() as manager:
        procs = []
        results = manager.list([None]*len(data))
        for index, value in enumerate(data):
            proc = mp.Process(target=expensive, args=(index, results, index))
            procs.append(proc)
            proc.start()

        for proc in procs:
            proc.join()

        print(results)

    # the above uses a Manager() to store the return values from each function
    # evaluation.  this can also be done (more easily) using a Pool
    print('--- Example 2 ---')
    with mp.Pool(processes=len(data)) as pool:
        print(pool.map(expensive, data))

    # limiting the pool size keeps resource utilization in check
    print('--- Example 3 ---')
    with mp.Pool(processes=4) as pool:
        print(pool.map(expensive, data))

