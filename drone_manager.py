# import library
import logging
import socket
import sys
import threading
import time

# membuat log data
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# jarak default 30 cm
DEFAULT_DISTANCE = 0.30

# class untuk mengatur drone
class DroneManager(object):
    # koneksi UDP untuk mengirim perintah dan menerima respon
    # host_ip='192.168.10.2' host_port=8889 untuk komputer
    # host_ip='192.168.10.2' host_port=8889 untuk drone
    def __init__(self, host_ip='192.168.10.2', host_port=8889,
                 drone_ip='192.168.10.1', drone_port=8889,
                 is_imperial=False):

        # set inisiasi dengan informasi komputer dan drone
        self.host_ip = host_ip
        self.host_port = host_port
        self.drone_ip = drone_ip
        self.drone_port = drone_port
        self.drone_address = (drone_ip, drone_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host_ip, self.host_port))

        #
        self.is_imperial = is_imperial

        # set instance untuk drone mengirim respon
        self.response = None
        self.stop_event = threading.Event()
        self._response_thread = threading.Thread(
            target=self.receive_response,
            args=(self.stop_event, ))
        self._response_thread.start()

        # set instance untuk pengirim perintah ke drone
        self.send_command('command')
        self.send_command('streamon')

    # fungsi untuk menerima response dari drone
    def receive_response(self, stop_event):
        while not stop_event.is_set():
            # log yang akan drone kirim
            try:
                self.response, ip = self.socket.recvfrom(3000)
                logger.info({'action': 'receive_response',
                             'response': self.response})
            except socket.error as ex:
                logger.error({'action': 'receive_response',
                             'ex': ex})
                break

    # fungsi untuk menghentikan paksa drone
    def __dell__(self):
        self.stop()

    # fungsi untuk memberhentikan drone
    def stop(self):
        self.stop_event.set()
        retry = 0

        # jika thread masih terbuka
        while self._response_thread.isAlive():
            time.sleep(0.3)
            if retry > 30:
                break
            retry += 1
        self.socket.close()

    # fungsi untuk mengirim perintah ke drone
    def send_command(self, command):
        logger.info({'action': 'send_command', 'command': command})
        self.socket.sendto(command.encode('utf-8'), self.drone_address)

        retry = 0
        # jika tidak ada respon dari drone
        while self.response is None:
            time.sleep(0.3)
            if retry > 3:
                break
            retry += 1
        if self.response is None:
            response = None
        else:
            response = self.response.decode('utf-8')
        self.response = None
        return response

    # fungsi untuk drone terbang
    def takeoff(self):
        return self.send_command('takeoff')

    # fungsi untuk drone mendarat
    def land(self):
        return self.send_command('land')

    # fungsi untuk menggerakan drone
    def move(self, direction, distance):
        distance = float(distance)
        #konversi satuan
        if self.is_imperial:
            distance = int(round(distance * 30.48))
        else:
            distance = int(round(distance * 100))
        return self.send_command(f'{direction} {distance}')

    # fungsi untuk drone bergerak ke atas
    def up(self, distance=DEFAULT_DISTANCE):
        return self.move('up', distance)

    # fungsi untuk drone bergerak ke bawah
    def down(self, distance=DEFAULT_DISTANCE):
        return self.move('down', distance)

    # fungsi untuk drone bergerak ke kiri
    def left(self, distance=DEFAULT_DISTANCE):
        return self.move('left', distance)

    # fungsi untuk drone bergerak ke kanan
    def right(self, distance=DEFAULT_DISTANCE):
        return self.move('right', distance)

    # fungsi untuk drone bergerak maju
    def forward(self, distance=DEFAULT_DISTANCE):
        return self.move('forward', distance)

    # fungsi untuk drone bergerak kebelakang
    def back(self, distance=DEFAULT_DISTANCE):
        return self.move('back', distance)

if __name__ == '__main__':
    drone_manager = DroneManager()

    drone_manager.takeoff()
    time.sleep(10)
    drone_manager.forward()
    time.sleep(5)
    drone_manager.right()
    time.sleep(5)
    drone_manager.back()
    time.sleep(5)
    drone_manager.left()
    time.sleep(5)
    drone_manager.up()
    time.sleep(5)
    drone_manager.down()
    time.sleep(5)


    drone_manager.land()
    drone_manager.stop()
