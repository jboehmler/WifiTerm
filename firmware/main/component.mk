#
# "main" component. Certificates are embedded at build time; copy them in from the output
# of tools/make-certs.sh (wifiterm/ca.crt, wifiterm/server.crt, wifiterm/server.key).
# server.key is never committed (.gitignore).
#
COMPONENT_EMBED_TXTFILES := ca.crt server.crt server.key

# Board: `make BOARD=shield` builds for the rs232-shield (TRS3243E, cable detect, `uart power
# auto`); `make BOARD=proto` for hardware/prototype (MAX3232 module + discrete cable detect);
# anything else is the bench build. Run `make clean` after changing it.
ifeq ($(BOARD),shield)
CFLAGS += -DBOARD=1
endif
ifeq ($(BOARD),proto)
CFLAGS += -DBOARD=2
endif
