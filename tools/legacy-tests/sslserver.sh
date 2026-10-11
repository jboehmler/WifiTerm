#!/bin/bash
#

if [ -z "$1" ]; then
    echo "Usage:  $0 <localhost|wifiterm> Exiting..."
    exit 1
fi
if [ "$1" == "localhost" ]; then
    HOST="localhost"
elif [ "$1" == "wifiterm" ]; then
    HOST="wifiterm"
else
    echo "Second parapmeter must be localhost or wifiterm.  Case matters."
    echo "Invalid host name <$HOST>.  Exiting..."
    exit 1
fi

if [ "$HOST" == "wifiterm" ]; then
    CACRT="wifiterm-certs.good/ca.crt"
    SERVERCRT="wifiterm-certs.good/server.crt"
    SERVERKEY="wifiterm-certs.good/server.key"

    HOST=192.168.4.1
    SERVERIP="192.168.4.1"
    CLIENTIP="192.168.4.2"
    SERVERPORT="8443"

elif [ "$HOST" == "localhost" ]; then
    CACRT="localhost-certs.good/ca.crt"
    SERVERCRT="localhost-certs.good/server.crt"
    SERVERKEY="localhost-certs.good/server.key"

    HOST=127.0.0.1
    SERVERIP="127.0.0.1"
    CLIENTIP="127.0.0.1"
    SERVERPORT="8443"
fi

echo "Using command line args:"
echo "  HOST:  $HOST"
echo "  CACRT:  $CACRT"
echo "  SERVERCRT:  $SERVERCRT"
echo "  SERVERKEY:  $SERVERKEY"
echo "  SERVERIP:  $SERVERIP"
echo "  CLIENTIP:  $CLIENTIP"
echo "  SERVERPORT:  $SERVERPORT"

# Requires client cert and provides server cert
openssl s_server -CAfile "$CACRT" \
    -key "$SERVERKEY" -cert "$SERVERCRT" \
    -Verify 1 -state -no_tls1_3 \
    -accept "$SERVERPORT"
