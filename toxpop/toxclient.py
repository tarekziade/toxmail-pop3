import asyncore
import json
from os.path import exists
from time import sleep
from threading import Thread
from tox import Tox
import json


SERVER = ["54.199.139.199", 33445,
"7F9C31FE850E97CEFD4C4591DF93FC757C7C12549DDD55F8EEAECC34FE76C029"]
DATA = 'data'
_ID = ('360E674BA34A8C761E9AE8858CCBFC8789A2A0FF9'
       'D42D2AF12340318D04A0E73FCC1E7314A7F')


class ToxClient(Thread, Tox):
    def __init__(self):
        Thread.__init__(self)
        self.messages = []
        if exists(DATA):
            self.load_from_file(DATA)
        self.running = False

    def run(self):
        self.set_name("ToxPop")
        print('ID: %s' % self.get_address())
        self.bootstrap_from_address(SERVER[0], 1, SERVER[1], SERVER[2])

        # loop until connected
        checked = False
        self.running = True
        try:
            while self.running:
                status = self.isconnected()

                if not checked and status:
                    print('Connected to DHT.')
                    checked = True

                if checked and not status:
                    print('Disconnected from DHT.')
                    self.connect()
                    checked = False

                self.do()
                sleep(0.01)
        except KeyboardInterrupt:
            pass

    def on_friend_message(self, friendId, message):
        message = json.loads(message)['data']
        self.messages.append([friendId, message])
        print 'Message stored'

    def stop(self):
        self.running = False
        self.join()
        self.kill()
