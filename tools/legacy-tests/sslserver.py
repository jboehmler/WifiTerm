import socket
import ssl

# host = 'localhost'
host = "127.0.0.1"
port = 8443

# Create socket and wrap with SSL
# Certificate and key paths
ca_cert = "localhost-certs/ca.crt"
# client_cert = 'localhost-certs/client.crt'
# client_key = 'localhost-certs/client.key'
server_cert = "localhost-certs/server.crt"
server_key = "localhost-certs/server.key"

print(f"Starting sslserver")

print(f"Create SSL context")
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

print(f"Load server certificate and key")
context.load_cert_chain(certfile=server_cert, keyfile=server_key)

print(f"Load the ca's certificate for verification")
context.load_verify_locations(cafile=ca_cert)

print(f"Enforce certificate verification")
context.verify_mode = ssl.CERT_REQUIRED

print(f"Starting socket")
# Create socket and wrap with SSL
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    print(f"Listening on {host}:{port}")
    sock.bind((host, port))
    sock.listen(5)
    print(f"Starting SSL")
    with context.wrap_socket(sock, server_side=True) as ssock:
        conn, addr = ssock.accept()
        print(f"Connected by {addr}")
        data = conn.recv(1024)
        print(f"Received: {data.decode()}")
        data = "Hello from server".encode()
        conn.sendall(data)
        print(f"Sent: {data.decode()}")
