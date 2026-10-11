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
    CLIENTCRT="wifiterm-certs.good/client.crt"
    CLIENTKEY="wifiterm-certs.good/client.key"

    HOST=192.168.4.1
    SERVERIP="192.168.4.1"
    CLIENTIP="192.168.4.2"

elif [ "$HOST" == "localhost" ]; then
    CACRT="localhost-certs.good/ca.crt"
    CLIENTCRT="localhost-certs.good/client.crt"
    CLIENTKEY="localhost-certs.good/client.key"

    HOST=127.0.0.1
    SERVERIP="127.0.0.1"
    CLIENTIP="127.0.0.1"
fi

echo "Using command line args:"
echo "  HOST:  $HOST"
echo "  CACRT:  $CACRT"
echo "  CLIENTCRT:  $CLIENTCRT"
echo "  CLIENTKEY:  $CLIENTKEY"
echo "  SERVERIP:  $SERVERIP"
echo "  CLIENTIP:  $CLIENTIP"

# Requires server cert and provides client cert
openssl s_client -CAfile "$CACRT"  -servername $HOST \
    -key "$CLIENTKEY" -cert "$CLIENTCRT" \
    -verify_return_error -no_tls1_3\
    -connect $HOST:8443
