import multiprocessing

bind = "0.0.0.0:10000"
workers = 1  # Only use 1 worker to reduce memory
timeout = 120  # Increase timeout
worker_class = "sync"
keepalive = 5
