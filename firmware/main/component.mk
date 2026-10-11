#
# "main" component. Certificates are embedded at build time; copy them in from the output
# of tools/make-certs.sh (wifiterm/ca.crt, wifiterm/server.crt, wifiterm/server.key).
# server.key is never committed (.gitignore).
#
COMPONENT_EMBED_TXTFILES := ca.crt server.crt server.key
