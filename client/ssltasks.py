import logging

import socket
import ssl
from pprint import pformat
from time import sleep

from tasks.iotask import IOTask

SOCKTIMEOUT = 15
# CONNTIMEOUT = 1
CONNTIMEOUT = .1
ESCKEY = chr(0x1B)

# ************************** Class SSLTask **************************
class SSLConn():
    # ************************** Defaults **************************
    def __init__(self):
        logging.debug(f"SSLConn __init__")
        # ssl info
        self.clear_host()
        self.servercert = None
        self.sslconn = None
        self.connected = False

    def set_host(self, hostaddr, hostport, server_sni_hostname, ca_cert, client_cert, client_key):
        # host info
        self.hostaddr = hostaddr
        self.hostport = hostport
        self.server_sni_hostname = server_sni_hostname
        self.ca_cert = ca_cert
        self.client_cert = client_cert
        self.client_key = client_key
        self.context = None
        self.hostset = True

    def clear_host(self):
        self.hostaddr = None
        self.hostport = None
        self.server_sni_hostname = None
        self.ca_cert = None
        self.client_cert = None
        self.client_key = None
        self.context = None
        self.hostset = False

    def is_hostset(self):
        # if any of the host settings are None, set hostset to and return False
        self.hostset = True
        match None:
            case self.hostaddr:
                self.hostset = False

            case self.hostport:
                self.hostset = False

            case self.server_sni_hostname:
                self.hostset = False

            case self.ca_cert:
                self.hostset = False

            case self.client_cert:
                self.hostset = False

            case self.client_key:
                self.hostset = False

            case self.context:
                self.hostset = False

            case _:
                logging.warning(f"SSLHost error default case")
                self.hostset = False

        return self.hostset

    def log_hostdata(self):
        logging.debug(f"SSLHost Host data:")
        logging.debug(f"SSLHost hostaddr <{self.hostaddr}>")
        logging.debug(f"SSLHost hostport <{self.hostport}>")
        logging.debug(f"SSLHost server_sni_hostname <{self.server_sni_hostname}>")
        logging.debug(f"SSLHost ca_cert <{self.ca_cert}>")
        logging.debug(f"SSLHost client_cert <{self.client_cert}>")
        logging.debug(f"SSLHost client_key <{self.client_key}>")
        logging.debug(f"SSLHost context <{self.context}>")
        logging.debug(f"SSLHost hostset <{self.hostset}>")

    def set_connected(self):
        logging.debug("SSLConn SSL set connected.")
        self.connected = True

    def set_disconnected(self):
        logging.debug("SSLConn SSL set disconnected.")
        self.connected = False

    def is_connected(self):
        logging.debug(f"SSLConn SSL check is_connected self.connected <{self.connected}>.")
        return self.connected

    def get_peercert(self):
        logging.debug("SSLConn SSL get peercert.")
        return self.servercert

    def connect(self):
        logging.debug("SSLConn SSLTask connect.")
        self.set_disconnected()

        self.context = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH, cafile=self.ca_cert
        )
        self.context.verify_mode = ssl.CERT_REQUIRED
        self.context.load_cert_chain(certfile=self.client_cert, keyfile=self.client_key)

        # print(f"Starting connection to {self.hostaddr}:{self.hostport}")
        logging.debug(f"SSLConn Start socket...")
        logging.debug(f"SSLConn Starting connection to {self.hostaddr}:{self.hostport}")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if not self.socket:
            print(f"Connection to {self.hostaddr}:{self.hostport} failed.")
            logging.critical(f"SSLConn Start socket FAILED.")
            return None

        self.socket.settimeout(SOCKTIMEOUT)
        # print(f"Encrypting connection to {self.hostaddr}:{self.hostport}")
        logging.debug(f"SSLConn SSL wrap socket...")
        self.sslconn = self.context.wrap_socket(
            self.socket, server_side=False, server_hostname=self.server_sni_hostname
        )
        try:
            logging.debug(f"SSLConn Start SSL connection...")
            self.sslconn.connect((self.hostaddr, self.hostport))

        except (TimeoutError, OSError):
            print(f"Connecting to host {self.hostaddr}:{self.hostport} failed.")
            print(f"Make sure host is up and try again.")
            exit(1)

        except ConnectionResetError:
            print(
                f"SSLConn SSL connection reset by host {self.hostaddr}:{self.hostport} failed."
            )
            print(f"Make sure host is up and try again.")
            exit(1)

        if not self.sslconn:
            print(f"Securing connection to {self.hostaddr}:{self.hostport}.")
            logging.debug(f"SSLConn Start SSL FAILED.")
            exit(1)

        self.servercert = self.sslconn.getpeercert()
        certstr = pformat(self.servercert)
        logging.debug(f"SSLConn Encrypted connection established. Peer:\r\n{certstr}")

        self.sslconn.settimeout(CONNTIMEOUT)
        self.set_connected()
        return True

    def recv(self, recvlen = 4094):
        logging.debug(f"SSLConn SSL recv recvlen <{recvlen}>.")
        readbuf = self.sslconn.recv(recvlen)
        logging.debug(f"SSLConn SSL recv readbuf <{readbuf}>.")
        if readbuf == b'':
            logging.debug(f"SSLConn SSL recv empty message:  <{readbuf}>.")
            logging.debug(f"SSLConn SSL recv connection closed?")
            logging.debug(f"SSLConn Set disconnected and sleep to let connection timeouts happen.")
            ssltask.set_disconnected()
            sleep(1)
            return False

        return readbuf

    def send(self, sendstr):
        # return None on success, non-None is error value
        logging.debug(f"SSLConn SSL send sendstr <{sendstr}>.")
        retval = self.sslconn.sendall(bytes(sendstr, "utf-8"))
        logging.debug(f"SSLConn SSL send retval <{retval}>.")
        return retval

    def close(self):
        # Shutdown the secure socket
        logging.debug("SSLConn SSL close.")
        self.set_disconnected()
        try:
            logging.debug("SSLConn Sending SSL close.")
            # Close the secure socket
            logging.debug("SSLConn Unwrap SSL connection.")
            self.sslconn.unwrap()
            logging.debug("SSLConn Closing SSL connection.")
            self.sslconn.close()
            logging.debug("SSLConn Closing TCP connection.")
            self.socket.close()

        except OSError:
            logging.debug("SSLConn Closing SSL connection got OSError exception.")

        logging.debug("Connection closed.")


# ************************** Class SSLIOTask **************************
class SSLIOTask(IOTask):
    # ************************** Defaults **************************
    def __init__(self):
        logging.debug(f"SSLIOTask __init__")

        logging.debug(f"Set up ssl connection.")
        self.sslconn = SSLConn()
        self.sslconn.set_disconnected()

        super().__init__("ssltask", self.input_func, self.output_func)
        logging.debug("Create SSLIOTasks recvtask sendtask.")

    def input_func():
        # return data from SSL connection or None
        logging.debug(f"input_func Start.")
        connected = self.sslconn.is_connected()
        logging.debug(f"input_func connected:  <{connected}>.")
        if not connected:
            logging.debug("input_func SSLIOTask SSL NOT CONNECTED.")
            sleep(1)
            return None

        logging.debug(f"input_func ssl recv...")
        readbuf = None
        try:
            readbuf = self.sslconn.recv(4094)

        except TimeoutError:
            logging.debug("input_func SSL recv timed out.")
            return None

        if readbuf == b'':
            logging.debug(f"input_func empty message:  <{readbuf}>.")
            logging.debug(f"input_func connection closed?  Set disconnected and sleep to let connection timeouts happen.")
            ssltask.sslconn.set_disconnected()
            sleep(1)
            return None

        msgstr = str(readbuf, "utf-8")
        logging.debug(f"input_func ssl message:  <{msgstr}>.")
        if msgstr:
            logging.debug(f"input_func return message:  <{msgstr}>.")
            return msgstr
        return None

    def output_func(sendstr):
        # send data to SSL connection
        # return unsent sendstr or None
        logging.debug(f"output_func Start.")
        connected = self.sslconn.is_connected()
        logging.debug(f"output_func connected:  <{connected}>.")
        if not connected:
            logging.debug("output_func SSLIOTask SSL NOT CONNECTED.")
            sleep(1)
            return None

        sendval = None
        try:
            sendval = self.sslconn.send(sendstr)

        except TimeoutError:
            logging.debug("Send timed out.")
            return sendstr

        except ssl.SSLEOFError:
            logging.debug("SSL EOF Error.")
            logging.debug(f"output_func connection closed?  Set disconnected and sleep to let connection timeouts happen.")
            self.sslconn.set_disconnected()
            return sendstr

        if sendval == None:
            logging.debug(f"output_func Message sent:  <{sendstr}>.")
            return None

        logging.debug(f"output_func sendval <{sendval}> is NOT NONE.")
        self.sslconn.set_disconnected()
        return sendstr


# ************************* SSLIOTask test functions **************************
def Test_SSLIOTask(host="wifiterm", DEBUGTIMEOUT=1):
    from time import sleep
    from pylib.psleep import psleep

    print(f"Starting test with host <{host}>...")
    ssl_tasks = SSLIOTask()
    if host == "wifiterm":
        ssl_tasks.sslconn.set_host("192.168.4.1", 443, "192.168.4.1",
                           "keys/wifiterm/ca.pem", "keys/wifiterm/client.pem",
                           "keys/wifiterm/client.key")
    else:
        ssl_tasks.sslconn.set_host("127.0.0.1", 8443, "127.0.0.1",
                           "keys/localhost/ca.crt", "keys/localhost/client.crt",
                           "keys/localhost/client.key")

    ssl_tasks.sslconn.log_hostdata()
    print(f"Starting SSL connection with <{host}>...")
    ssl_tasks.sslconn.connect()
    print(f"SSL connection with <{host}> complete.")

    print("Start tasks.")
    ssl_tasks.start()
    psleep(DEBUGTIMEOUT, "SSL tasks starting...")

    print()
    print("Test SSL send and receive.")
    print("Echoes what's typed in server back to server.  Send ping if nothing received.")
    print("Type <ESC> <Enter> or End <Enter> to quit.")
    print("Typing quit in the server makes IT close the connection and hangs this client.")
    print("Type in server now...")
    retstr = ""
    while ssl_tasks.sslconn.is_connected():
        logging.debug(f"Starting echo...")
        retstr = ssl_tasks.get() # get ssl server data from queue
        logging.debug(f"ssl_tasks get retstr <{retstr}>")
        if retstr:
            retstr = retstr.strip()
            if retstr[0] == ESCKEY:
                print()
                print("Break key received.")
                print("Ending program.")
                break

            if retstr == "End":
                print()
                print("End received.")
                print("Ending program.")
                break

            logging.debug(f"SSL received:  <{retstr}>.")
            print(f"Received <{retstr}>.")
            sendstr = f"ECHO:  <{retstr}>"
            ssl_tasks.sslconn.send(f"{sendstr}\n")
            logging.debug(f"ssl_tasks send:  <{sendstr}>.")
            print(f"Sent <{sendstr}>.")

        else:
            logging.debug(f"SSL retstr EMPTY:  send ping.")
            ssl_tasks.sslconn.send("ping") # send data for ssl server into queue
            #print(f"Sleep {DEBUGTIMEOUT} secs.")
            sleep(DEBUGTIMEOUT)

        ssl_tasks.sync_connected()  # is this needed since recv and send do for ssltask?
    print("Main loop ended.")

    print(f"Stopping tasks.")
    ssl_tasks.stop()

    print(f"Waiting for tasks to stop in case they're blocked.")
    print(f"Waiting for recvtask to unblock.")
    ssl_tasks.recvtask.wait_blocked()
    print(f"Waiting for sendtask to unblock.")
    ssl_tasks.sendtask.wait_blocked()

    print(f"Closing SSL connection.")
    ssl_tasks.sslconn.close()

    print(f"End of test.")


if __name__ == "__main__":
    Test_SSLIOTask('localhost')
