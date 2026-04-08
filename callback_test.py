from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        print("PATH:", parsed.path)
        print("QUERY:", query)

        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Callback received. You can close this tab.")

server = HTTPServer(("127.0.0.1", 8888), Handler)
print("Listening on http://127.0.0.1:8888")
server.handle_request()