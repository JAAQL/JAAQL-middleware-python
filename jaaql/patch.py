def monkey_patch():
    from psycopg2cffi import compat
    compat.register()

    from gevent import monkey
    from psycogreen import gevent
    monkey.patch_all()
    gevent.patch_psycopg()

    import requests_unixsocket
    requests_unixsocket.monkeypatch()
