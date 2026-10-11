#!/usr/bin/python3

import socket
import ssl
import pprint
from time import sleep

USE_HOST = "wifiterm"
# USE_HOST = "localhost"

# Server details
if USE_HOST == "wifiterm":
    # wifiterm
    host = "192.168.4.1"
    port = 8443

    # Certificate and key paths
    ca_cert = "wifiterm-certs.good/ca.crt"
    client_cert = "wifiterm-certs.good/client.crt"
    client_key = "wifiterm-certs.good/client.key"

else:
    # localhost
    host = "127.0.0.1"
    port = 8443

    ca_cert = "localhost-certs.good/ca.crt"
    client_cert = "localhost-certs.good/client.crt"
    client_key = "localhost-certs.good/client.key"

# def get_server_certificate(host, port):
#    try:
#        certificate = ssl.get_server_certificate((host, port))
#        return certificate
#    except Exception as e:
#        return f"Error: {e}"
#
# certificate = get_server_certificate(host, port)
#
# if "Error" not in certificate:
#    print(certificate)
# else:
#    print(certificate)

print(f"Create SSL context")
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
if context:
    print(f"...loaded.")

print(f"Load client certificate and key")
if context.load_cert_chain(certfile=client_cert, keyfile=client_key):
    print(f"...loaded.")

print(f"Load the ca's certificate for verification")
if context.load_verify_locations(cafile=ca_cert):
    print(f"...loaded.")

print(f"Enforce certificate verification")
context.verify_mode = ssl.CERT_REQUIRED

print(f"Create socket and wrap with SSL")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ssl_sock = context.wrap_socket(sock, server_hostname=host)
if sock and ssl_sock:
    print(f"...SSL socket ready.")

conncnt = 0
msgcnt = 0
# Connect to the server
ssl_sock.connect((host, port))
print(f"Connected to {host}:{port} using SSL")

cert = ssl_sock.getpeercert()
pprint.pprint(cert)
while 1:
    conncnt += 1
    # Send data
    message = f"Hello {conncnt} from client!"
    ssl_sock.sendall(message.encode())
    print(f"Sent: {message}")

    # Receive response
    data = ssl_sock.recv(1024)
    print(f"Received: {data.decode()}")

ssl_sock.shutdown(socket.SHUT_RDWR)

#    except ssl.SSLError as e:
#        print(f"SSL error: {e}")
#    except socket.error as e:
#        print(f"Socket error: {e}")
#    finally:
#        sleep(1)
#        ssl_sock.close()
