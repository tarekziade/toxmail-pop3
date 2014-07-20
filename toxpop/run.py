# inspired from
# http://code.activestate.com/recipes/534131-toxpop-python-pop3-server/
import logging
import os
import socket
import sys
import traceback

logging.basicConfig(format="%(name)s %(levelname)s - %(message)s")
log = logging.getLogger("toxpop")
log.setLevel(logging.INFO)

from toxpop.toxclient import ToxClient


class Connection(object):
    END = "\r\n"
    def __init__(self, conn):
        self.conn = conn

    def __getattr__(self, name):
        return getattr(self.conn, name)

    def sendall(self, data, END=END):
        if len(data) < 50:
            log.debug("send: %r", data)
        else:
            log.debug("send: %r...", data[:50])
        data += END
        self.conn.sendall(data)

    def recvall(self, END=END):
        data = []
        while True:
            chunk = self.conn.recv(4096)
            if END in chunk:
                data.append(chunk[:chunk.index(END)])
                break
            data.append(chunk)
            if len(data) > 1:
                pair = data[-2] + data[-1]
                if END in pair:
                    data[-2] = pair[:pair.index(END)]
                    data.pop()
                    break
        log.debug("recv: %r", "".join(data))
        return "".join(data)


class Message(object):
    def __init__(self, filename):
        msg = open(filename, "a+")
        try:
            self.data = data = msg.read()
            self.size = len(data)
            if data == '':
                self.top, self.bot = '', ''
            else:
                self.top, bot = data.split("\r\n\r\n", 1)
                self.bot = bot.split("\r\n")
        finally:
            msg.close()


class Handler(object):

    def __init__(self):
        self.tox = ToxClient()

    def start(self):
        self.tox.start()

    def stop(self):
        self.tox.stop()

    def USER(self, data):
        return "+OK user accepted"

    def PASS(self, data):
        return "+OK pass accepted"

    def STAT(self, data):
        num = len(self.tox.messages)
        total = 0
        for friend_id, msg in self.tox.messages:
            total += len(msg)

        return "+OK %d %i" % (num, total)

    def LIST(self, data):
        num = len(self.tox.messages)
        total = 0
        res = []

        for index, msg in enumerate(self.tox.messages):
            friend_id, msg = msg
            total += len(msg)
            res.append("%d %d" % (index+1, len(msg)))

        res.insert(0, "+OK %d messages (%i octets)" % (num, total))
        res = "\r\n".join(res) + "\r\n."
        return res

    def TOP(self, data):
        import pdb; pdb.set_trace()
        cmd, num, lines = data.split()
        assert num == "1", "unknown message number: %s" % num
        lines = int(lines)
        text = msg.top + "\r\n\r\n" + "\r\n".join(msg.bot[:lines])
        return "+OK top of message follows\r\n%s\r\n." % text

    def RETR(self, data):
        log.info("message sent")
        index = int(data.split()[-1]) - 1
        msg = self.tox.messages[index][-1]
        return "+OK %i octets\r\n%s\r\n." % (len(msg), msg)

    def DELE(self, data):
        index = int(data.split()[-1]) - 1
        self.tox.messages.pop(index)
        return "+OK message %d deleted" % (index + 1)

    def NOOP(self, data):
        return "+OK"

    def QUIT(self, data):
        return "+OK toxpop POP3 server signing off"


def serve(host, port):
    handler = Handler()
    handler.start()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    try:
        if host:
            hostname = host
        else:
            hostname = "localhost"
        log.info("toxpop POP3 on %s:%s", hostname, port)
        while True:
            sock.listen(1)
            conn, addr = sock.accept()
            log.debug('Connected by %s', addr)
            try:

                conn = Connection(conn)
                conn.sendall("+OK toxpop file-based pop3 server ready")
                while True:
                    data = conn.recvall()
                    print data
                    command = data.split(None, 1)[0]
                    try:
                        cmd = getattr(handler, command)
                    except AttributeError:
                        conn.sendall("-ERR unknown command")
                    else:
                        conn.sendall(cmd(data))
                        if command is 'QUIT':
                            break
            finally:
                conn.close()
                msg = None
    except (SystemExit, KeyboardInterrupt):
        log.info("toxpop stopped")
    except Exception, ex:
        log.critical("fatal error", exc_info=ex)
    finally:
        try:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
        except Exception:
            pass
        handler.stop()


def main():
    if len(sys.argv) != 2:
        print "USAGE: [<host>:]<port>"
    else:
        _, port = sys.argv
        if ":" in port:
            host = port[:port.index(":")]
            port = port[port.index(":") + 1:]
        else:
            host = ""
        try:
            port = int(port)
        except Exception:
            print "Unknown port:", port
        else:
            serve(host, port)
