import os
import re
import traceback
from datetime import datetime
from socket import socket
from threading import Thread
from typing import Tuple, Optional

from henango.http.request import HTTPRequest
from henango.http.response import HTTPResponse
from urls import URL_VIEW

class WorkerThread(Thread):
    # 実行ファイルのあるディレクトリ
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # 静的配信ファイルを置くディレクトリ
    STATIC_ROOT = os.path.join(BASE_DIR, "static")

    # 拡張子とMIME Typeの対応
    MIME_TYPES = {
        "html": "text/html; charset=UTF-8",
        "css": "text/css",
        "png": "image/png",
        "jpg": "image/jpg",
        "gif": "image/gif",
    }

    STATUS_LINES = {
      200: "200 OK",
      404: "404 Not Found",
      405: "405 Method Not Allowed",
    }

    def __init__(self, client_socket: socket, address: Tuple[str, int]):
        super().__init__()

        self.client_socket = client_socket
        self.client_address = address
    
    def run(self) -> None:
        """
        クライアントと接続ずみのsocketを引数として受け取り
        リクエストを処理してレスポンスを送信する
        """

        try:

            # クライアントから送られたデータを受け取る
            request_bytes = self.client_socket.recv(4096)

            # クライアントから送られたデータをファイルに書き出す
            with open("server_recv.txt","wb") as f:
                f.write(request_bytes)

            # HTTPリクエストをパースする
            request = self.parse_http_request(request_bytes)

            if request.path in URL_VIEW:
                view = URL_VIEW[request.path]
                response = view(request)

            #pathがそれ以外の時は、静的ファイルからレスポンスを生成する
            else:
                try:
                  response_body = self.get_static_file_content(request.path)
                  content_type = None
                  response = HTTPResponse(body=response_body, content_type=content_type, status_code=200)

                except OSError:
                  # レスポンスを取得できなかった場合は、ログを出力して404を返す
                  traceback.print_exc()

                  response_body = b"<html><body><h1>404 Not Found</h1></body></html>"
                  content_type = "text/html;"
                  response = HTTPResponse(body=response_body, content_type=content_type, status_code=404)

            # レスポンスラインを生成
            response_line = self.build_response_line(response)
            # レスポンスヘッダーを生成
            response_header = self.build_response_header(response, request)

            # レスポンス全体を生成する
            response_bytes = (response_line + response_header + "\r\n").encode() + response_body

            self.client_socket.send(response_bytes)

        except Exception:
          # リクエストの処理中に例外が発生した場合はコンソールにエラーログを出力し
          # 処理を続行する
          print("=== Worker: リクエストの処理中にエラーが発生しました ===")
          traceback.print_exc()

        finally:
          # 例外が発生した場合もしなかった場合もTCPのcloseは行う
          print(f"=== Worker: クライアントとの通信を終了します remote_address: {self.client_address} ===")
          self.client_socket.close()

    def parse_http_request(self, request: bytes) -> HTTPRequest:
      # リクエスト全体を
      # 1.リクエストライン(1行目)
      # 2.リクエストヘッダー（２行目〜空行)
      # 3.リクエストボディ(空行~)
      # にパースする
      request_line, remain = request.split(b"\r\n", maxsplit=1)
      request_header, request_body = remain.split(b"\r\n\r\n", maxsplit=1)

      # リクエストラインをパースする
      method, path, http_version = request_line.decode().split(" ")

      # リクエストヘッダーを辞書にパースする
      headers = {}
      for header_row in request_header.decode().split("\r\n"):
          key, value = re.split(r": *", header_row, maxsplit=1)
          headers[key] = value

      return HTTPRequest(method=method, path=path, http_version=http_version, headers=headers, body=request_body)

    def get_static_file_content(self, path: str) -> bytes:
        """
        リクエストpathから、staticファイルの内容を取得する
        """

        # pathの先頭の/を削除し、相対パスにしておく
        relative_path = path.lstrip("/")
        # ファイルのpathを取得
        static_file_path = os.path.join(self.STATIC_ROOT, relative_path)

        with open(static_file_path, "rb") as f:
          return f.read()

    def build_response_line(self, response: HTTPResponse) -> str:
      """
      レスポンスラインを構築する
      """
      status_line = self.STATUS_LINES[response.status_code]
      return f"HTTP/1.1 {status_line}"

    def build_response_header(self, response: HTTPResponse, request: HTTPRequest) -> str:
        """
        レスポンスヘッダーを構築する
        """
        # Content-Typeが指定されていない場合はpathから特定する
        if response.content_type is None:
          # pathから拡張子を取得
          if "." in request.path:
            ext = request.path.rsplit(".",maxsplit=1)[-1]
          else:
            ext = ""
          # 拡張子からMIME Typeを取得
          # 知らない対応していない拡張子の場合はoctet-streamとする
          response.content_type = self.MIME_TYPES.get(ext, "application/octet-stream")


        # レスポンスヘッダーを生成
        response_header = ""
        response_header += f"Date: {datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}\r\n"
        response_header += "Host: HenaServer/0.1\r\n"
        response_header += f"Content-Length: {len(response.body)}\r\n"
        response_header += "Connection: Close\r\n"
        response_header += f"Content-Type: {response.content_type}\r\n"

        return response_header

