import random

def run_1d6():
    return int(random.uniform(1, 7))

def run_3d6():
    return run_1d6() + run_1d6() + run_1d6()
