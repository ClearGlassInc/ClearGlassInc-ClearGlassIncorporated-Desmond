from http.server import BaseHTTPRequestHandler, HTTPServer
class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path!="/health":
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
        self.wfile.write(b'{"gateway_up":true,"environment":"isolated-disposable-test"}')
    def log_message(self,*_args): return
if __name__=="__main__": HTTPServer(("127.0.0.1",18080),Health).serve_forever()
