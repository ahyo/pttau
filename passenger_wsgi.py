# Minimal ASGI -> WSGI adapter (HTTP only) inline untuk Passenger + FastAPI
import os, sys, io, asyncio

# pastikan cwd dan sys.path benar
APP_DIR = os.path.dirname(__file__)
os.chdir(APP_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


def _build_scope_from_environ(environ):
    # headers
    headers = []
    for k, v in environ.items():
        if k.startswith("HTTP_"):
            name = k[5:].replace("_", "-").lower().encode("latin-1")
            headers.append((name, v.encode("latin-1")))
    if "CONTENT_TYPE" in environ and environ["CONTENT_TYPE"]:
        headers.append((b"content-type", environ["CONTENT_TYPE"].encode("latin-1")))
    if "CONTENT_LENGTH" in environ and environ["CONTENT_LENGTH"]:
        headers.append((b"content-length", environ["CONTENT_LENGTH"].encode("latin-1")))

    # client/server
    client = (environ.get("REMOTE_ADDR", None), int(environ.get("REMOTE_PORT", 0) or 0))
    server = (environ.get("SERVER_NAME", ""), int(environ.get("SERVER_PORT", 0) or 0))

    # path & query
    raw_path = environ.get("PATH_INFO", "")
    path = raw_path if raw_path.startswith("/") else "/" + raw_path
    qs = environ.get("QUERY_STRING", "").encode("latin-1")

    scope = {
        "type": "http",
        "http_version": environ.get("SERVER_PROTOCOL", "HTTP/1.1").split("/")[1],
        "method": environ.get("REQUEST_METHOD", "GET"),
        "scheme": environ.get("wsgi.url_scheme", "http"),
        "path": path,
        "raw_path": path.encode("latin-1", "ignore"),
        "query_string": qs,
        "headers": headers,
        "client": client,
        "server": server,
    }
    return scope


def _read_body(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError:
        length = 0
    wsgi_input = environ.get("wsgi.input")
    if not wsgi_input or length == 0:
        return b""
    return wsgi_input.read(length)


def asgi_to_wsgi(app):
    """Return a WSGI application that runs the given ASGI app (HTTP only, no websockets/streaming)."""

    def wsgi_app(environ, start_response):
        scope = _build_scope_from_environ(environ)
        body_bytes = _read_body(environ)
        # ASGI receive/send
        received = {"sent": False}
        response_started = {"done": False}
        status_line = {"value": "500 Internal Server Error"}
        resp_headers = []

        async def receive():
            if not received["sent"]:
                received["sent"] = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        chunks = []

        async def send(message):
            mtype = message.get("type")
            if mtype == "http.response.start":
                status = message.get("status", 200)
                headers = message.get("headers", [])
                status_line["value"] = f"{status} {'OK' if status==200 else ''}".strip()
                # decode headers from bytes
                resp_headers.clear()
                for k, v in headers:
                    resp_headers.append((k.decode("latin-1"), v.decode("latin-1")))
                response_started["done"] = True
            elif mtype == "http.response.body":
                chunks.append(message.get("body", b"") or b"")
            else:
                # ignore other types for this minimal adapter
                pass

        async def app_task():
            await app(scope, receive, send)

        # run the ASGI app
        try:
            asyncio.run(app_task())
        except Exception as e:
            # jika app crash, tampilkan pesan ringkas
            err = f"ASGI app error: {e}"
            sys.stderr.write(err + "\n")
            start_response(
                "500 Internal Server Error",
                [("Content-Type", "text/plain; charset=utf-8")],
            )
            return [err.encode("utf-8")]

        if not response_started["done"]:
            # jika app tidak memanggil http.response.start, set default
            status_line["value"] = "200 OK"
            resp_headers.append(("Content-Type", "text/plain; charset=utf-8"))

        start_response(status_line["value"], resp_headers)
        return [b"".join(chunks)]

    return wsgi_app


# Import FastAPI app dan bungkus
from app.main import app as asgi_app

application = asgi_to_wsgi(asgi_app)
