from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404); self.end_headers(); return
        body=json.dumps({
            "gateway_state":"healthy",
            "test_mode":True,
            "environment":"isolated-disposable-test",
            "production_status":"not_production"
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self,*_args):
        return

if __name__=="__main__":
    HTTPServer(("10.77.0.1",18080),Health).serve_forever()
