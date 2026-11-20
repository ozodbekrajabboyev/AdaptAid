import os

# implicit's ALS and numpy's BLAS should not spawn a thread per core inside a web server.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
