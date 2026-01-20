# Gunicorn configuration for .smash
bind = "127.0.0.1:8000"
workers = 2
threads = 2
worker_class = "sync"
timeout = 30
keepalive = 2

# Logging
accesslog = "logs/gunicorn-access.log"
errorlog = "logs/gunicorn-error.log"
loglevel = "info"

# Process naming
proc_name = "smash"
