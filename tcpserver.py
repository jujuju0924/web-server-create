import socket

class TCPServer:
  """
  TCP通信を行うサーバーを表すクラス
  """
  def serve(self):
    """
    サーバーを起動する
    """

    print("=== サーバーを起動します ===")

    try:
      # socketを生成
      server_socket = socket.socket()
      server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

      # socketをlocalhostのポート番号8080番に割り当てる
      server_socket.bind(("localhost",8080))
      server_socket.listen(10)

      # 外部からの接続を待ち、接続があったらコネクションを確立する
      print("=== クライアントからの接続を待ちます ===")
      (client_socket, address) = server_socket.accept()
      print(f"=== クライアントからの接続が完了しました remote_address: {address} ===")