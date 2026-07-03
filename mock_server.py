#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


class MockHandler(BaseHTTPRequestHandler):
    server_version = "APIMock/1.0"

    def send_json(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path in ("/products", "/product/getProducts"):
            self.send_json(
                200,
                {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "total": 2,
                        "list": [
                            {"productId": 1001, "name": "demo product", "price": 99},
                            {"productId": 1002, "name": "sample product", "price": 199},
                        ],
                    },
                },
            )
        elif parsed.path in ("/products/detail", "/product/getById"):
            product_id = query.get("productId", ["1001"])[0]
            self.send_json(
                200,
                {
                    "code": 200,
                    "message": "success",
                    "data": {"productId": product_id, "name": "demo product", "price": 99},
                },
            )
        elif parsed.path == "/shop/getShops":
            self.send_json(200, {"code": 200, "message": "success", "data": {"list": [{"shopId": 1, "shopName": "demo shop"}]}})
        elif parsed.path in ("/cart", "/cart/getCart"):
            if not self.headers.get("Authorization"):
                self.send_json(401, {"code": 401, "message": "missing token"})
            else:
                self.send_json(200, {"code": 200, "message": "success", "data": {"items": []}})
        elif parsed.path == "/order/getAll":
            self.send_json(200, {"code": 200, "message": "success", "data": {"total": 0, "list": []}})
        else:
            self.send_json(404, {"code": 404, "message": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self.read_json()
        if parsed.path in ("/auth/login", "/app/login"):
            if body.get("phone") and body.get("password"):
                self.send_json(200, {"code": 200, "message": "success", "data": {"token": "mock-token-123", "userId": 1}})
            else:
                self.send_json(400, {"code": 400, "message": "phone/password required"})
        else:
            self.send_json(404, {"code": 404, "message": "not found"})

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


def main():
    server = HTTPServer(("127.0.0.1", 19007), MockHandler)
    print("mock server listening: http://127.0.0.1:19007")
    server.serve_forever()


if __name__ == "__main__":
    main()
