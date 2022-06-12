workers = 5
worker_class = "gevent"
worker_connections = 100
enable_stdio_inheritance = True
proc_name = "jaaql-middleware-python"
preload_app = True

has_checked_for_install = False


def post_worker_init(worker):
    worker.wsgi.model.set_jaaql_lookup_connection()


def child_exit(server, worker):
    global has_checked_for_install
    if not has_checked_for_install:
        import os
        if os.path.exists(os.path.join("vault", "was_installed")):
            os.unlink(os.path.join("vault", "was_installed"))
            has_checked_for_install = True
            print("Halting server. If this step fails, make sure you haven't started any non daemonic threads. When "
                  "creating your threads. Set daemon=True in the constructor to make sure the server can properly "
                  "restart")
            server.halt()
    has_checked_for_install = True
