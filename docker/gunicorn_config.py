workers = 5
worker_class = "gevent"
worker_connections = 100
enable_stdio_inheritance = True
proc_name = "jaaql-middleware-python"
preload_app = True

has_checked_for_install = False


def child_exit(server, worker):
    global has_checked_for_install
    if not has_checked_for_install:
        import os
        if os.path.exists(os.path.join("vault", "was_installed")):
            os.unlink(os.path.join("vault", "was_installed"))
            has_checked_for_install = True
            server.halt()
    has_checked_for_install = True
