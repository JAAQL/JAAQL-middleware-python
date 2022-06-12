def monkey_patch():
    from gevent import monkey
    monkey.patch_all()

    import requests_unixsocket
    requests_unixsocket.monkeypatch()
