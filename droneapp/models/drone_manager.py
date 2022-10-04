# import library
import logging
import contextlib
import socket
import sys
import threading
import time

# membuat log data
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# jarak default 30 cm
DEFAULT_DISTANCE = 0.30

# kecepatan default 10 cm/s
DEFAULT_SPEED= 10

# kecepatan derajat putaran
DEFAULT_DEGREE = 10

# class untuk mengatur drone
class DroneManager(object):
    # koneksi UDP untuk mengirim perintah dan menerima respon
    # host_ip='192.168.10.2' host_port=8889 untuk komputer
    # host_ip='192.168.10.2' host_port=8889 untuk drone
    def __init__(self, host_ip='192.168.10.2', host_port=8889,
                 drone_ip='192.168.10.1', drone_port=8889,
                 is_imperial=False, speed=DEFAULT_SPEED):

        # set inisiasi dengan informasi komputer dan drone
        self.host_ip = host_ip
        self.host_port = host_port
        self.drone_ip = drone_ip
        self.drone_port = drone_port
        self.drone_address = (drone_ip, drone_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host_ip, self.host_port))

        # mengatur satuan imperial
        self.is_imperial = is_imperial

        # inisiasi kecepatan
        self.speed = speed

        # set instance untuk drone mengirim respon
        self.response = None
        self.stop_event = threading.Event()
        self._response_thread = threading.Thread(
            target=self.receive_response,
            args=(self.stop_event, ))
        self._response_thread.start()

        # set instance untuk drone melakukan patroli
        self.patrol_event = None
        self.is_patrol = False
        self._patrol_semaphore = threading.Semaphore(1)
        self._thread_patrol = None

        # set instance untuk pengirim perintah ke drone
        self.send_command('command')
        self.send_command('streamon')
        self.set_speed(self.speed)

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

    # fungsi untuk drone mengatur kecepatan
    def set_speed(self, speed):
        return self.send_command(f'speed {speed}')

    # fungsi untuk drone berputar searah jarum jam
    def clockwise(self,degree=DEFAULT_DISTANCE):
        return self.send_command(f'cw{degree}')

    # fungsi untuk drone berputar berlawanan searah jarum jam
    def counter_clockwise(self, degree=DEFAULT_DISTANCE):
        return self.send_command(f'ccw {degree}')

    # fungsi untuk drone berbalik ke depan
    def flip_front(self):
        return self.send_command('flip f')

    # fungsi untuk drone berbalik ke belakang
    def flip_back(self):
        return self.send_command('flip b')

    # fungsi untuk drone berbalik ke kiri
    def flip_left(self):
        return self.send_command('flip l')

    # fungsi untuk drone berbalik ke kanan
    def flip_right(self):
        return self.send_command('flip r')

    # fungsi untuk drone berpatroli
    def patrol(self):
        if not self.is_patrol:
            self.patrol_event = threading.Event()
            self._thread_patrol = threading.Thread(
                target=self._patrol,
                args=(self._patrol_semaphore, self.patrol_event,))
            self._thread_patrol.start()
            self.is_patrol = True

    # fungsi untuk berhenti patroli
    def stop_patrol(self):
        if self.is_patrol:
            self.patrol_event.set()
            retry = 0
            while self._thread_patrol.isAlive():
                time.sleep(0.3)
                if retry > 300:
                    break
                retry += 1
            self.is_patrol = False

    # fungsi untuk rute drone patroli
    def _patrol(self, semaphore, stop_event):
        is_acquire = semaphore.acquire(blocking=False)
        if is_acquire:
            logger.info({'action': '_patrol', 'status': 'acquire'})
            with contextlib.ExitStack() as stack:
                stack.callback(semaphore.release)
                status = 0
                while not stop_event.is_set():
                    status += 1
                    if status == 1:
                        self.up()
                    if status == 2:
                        self.clockwise(90)
                    if status == 3:
                        self.down()
                    if status == 4:
                        status = 0
                    time.sleep(5)
        else:
            logger.warning({'action': '_patrol', 'status': 'not_acquire'})
