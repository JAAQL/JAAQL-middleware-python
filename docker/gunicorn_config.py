import threading
import signal

worker_class = "gevent"
worker_connections = 100
enable_stdio_inheritance = True
proc_name = "jaaql-middleware-python"
preload_app = True

has_checked_for_install = False


def when_ready(server):
    # preload_app has already built the app in this master and no worker has forked yet, so installing
    # here starts every worker installed. The migrations manager's HTTP install still works as a fallback
    # if this raises - it installs inside one worker and then bounces the whole master through child_exit
    # below, which is a second gunicorn boot on every fresh container.
    try:
        server.app.wsgi().model.install_on_bootup()
    except Exception:
        import traceback
        traceback.print_exc()


def post_worker_init(worker):
    import signal

    worker.wsgi.model.set_jaaql_lookup_connection()

    def my_signal_handler(signum, frame):
        worker.wsgi.model.reload_cache()

    signal.signal(signal.SIGUSR1, my_signal_handler)


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
            pid = server.pid
            threading.Thread(target=lambda: os.kill(pid, signal.SIGQUIT)).start()
    has_checked_for_install = True
