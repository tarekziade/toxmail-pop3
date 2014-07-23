# inspired from
# http://code.activestate.com/recipes/534131-toxpop-python-pop3-server/
import logging
import os
import socket
import sys
import traceback
import mailbox


logging.basicConfig(format="%(name)s %(levelname)s - %(message)s")
log = logging.getLogger("toxpop")
log.setLevel(logging.INFO)



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



class Handler(object):

    def __init__(self, maildir='mails'):
        self.maildir = mailbox.Maildir(maildir)

    def USER(self, data):
        return "+OK user accepted"

    def PASS(self, data):
        return "+OK pass accepted"

    def STAT(self, data):
        num = len(self.maildir)
        total = 0

        for msg in self.maildir:
            num += 1
            total += len(str(msg))

        return "+OK %d %i" % (num, total)

    def _get_sorted(self):
        mails = [(key, msg) for key, msg in self.maildir.iteritems()]
        mails.sort()
        return mails

    def LIST(self, data):
        num = len(self.maildir)
        total = 0
        res = []
        index = 0

        for key, msg in self._get_sorted():
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
        index = int(data.split()[-1]) - 1
        __, msg = self._get_sorted()[index]
        return "+OK %i octets\r\n%s\r\n." % (len(msg), msg)

    def DELE(self, data):
        index = int(data.split()[-1]) - 1
        key, __ = self._get_sorted()[index]
        self.maildir.lock()
        try:
            self.maildir.remove(key)
            self.maildir.flush()
        finally:
            self.maildir.unlock()
        return "+OK message %d deleted" % (index + 1)

    def NOOP(self, data):
        return "+OK"

    def QUIT(self, data):
        return "+OK toxpop POP3 server signing off"


def serve(host, port, maildir):
    handler = Handler(maildir)

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


def main():
    if len(sys.argv) != 3:
        print "USAGE: port maildir"
    else:
        _, port, maildir = sys.argv
        port = int(port)
        serve('localhost', port, maildir)
