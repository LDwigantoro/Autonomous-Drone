# import library
import logging
import contextlib
import os
import socket
import subprocess
import sys
import threading
import time

import cv2 as cv
import numpy as np

from droneapp.models.base import Singleton

# membuat log data
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# jarak default 30 cm
DEFAULT_DISTANCE = 0.30

# kecepatan default 10 cm/s
DEFAULT_SPEED = 10

# kecepatan derajat putaran
DEFAULT_DEGREE = 10

# Ukuran frame video streaming
FRAME_X = int(960/3)
FRAME_Y = int(720/3)
FRAME_AREA = FRAME_X * FRAME_Y

FRAME_SIZE = FRAME_AREA * 3
FRAME_CENTER_X = FRAME_X / 2
FRAME_CENTER_Y = FRAME_Y / 2

CMD_FFMPEG = (f'ffmpeg -hwaccel auto -hwaccel_device opencl -i pipe:0 '
              f'-pix_fmt bgr24 -s {FRAME_X}x{FRAME_Y} -f rawvideo pipe:1')

# Membuat jalur xml file
FACE_DETECT_XML_FILE = './droneapp/models/haarcascade_frontalface_default.xml'

class ErrorNoFaceDetectXMLFile(Exception):
    """Error No Face Detect XML File"""

# class untuk mengatur drone
class DroneManager(metaclass=Singleton):
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

        # set instance untuk frame video drone
        self.proc = subprocess.Popen(CMD_FFMPEG.split(' '),
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)
        self.proc_stdin = self.proc.stdin
        self.proc_stdout = self.proc.stdout

        self.video_port = 11111

        self._receive_video_thread = threading.Thread(
            target=self.receive_video,
            args=(self.stop_event, self.proc_stdin,
                  self.host_ip, self.video_port,))
        self._receive_video_thread.start()

        # jika tidak ada file XML
        if not os.path.exists(FACE_DETECT_XML_FILE):
            raise ErrorNoFaceDetectXMLFile(f'No {FACE_DETECT_XML_FILE}')
        self.face_cascade = cv.CascadeClassifier(FACE_DETECT_XML_FILE)
        self._is_enable_face_detect = False

        # menyimpan respon drone ke thread
        self._command_semaphore = threading.Semaphore(1)
        self._command_thread = None

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
        os.kill(self.proc.pid, 9)
        import signal
        os.kill(self.proc.pid, signal.CTRL_C_EVENT)

    # fungsi utama untuk mengirim perintah ke drone
    def send_command(self, command, blocking=True):
        self._command_thread = threading.Thread(
            target=self._send_command,
            args=(command, blocking,))
        self._command_thread.start()

    # fungsi untuk mengirim perintah ke drone
    def _send_command(self, command, blocking=True):
        is_acquire = self._command_semaphore.acquire(blocking=blocking)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self._command_semaphore.release)
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
        else:
            logger.warning({'action': 'send_command', 'command': command, 'status': 'not_acquire'})

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
    def clockwise(self, degree=DEFAULT_DEGREE):
        return self.send_command(f'cw {degree}')

    # fungsi untuk drone berputar berlawanan searah jarum jam
    def counter_clockwise(self, degree=DEFAULT_DEGREE):
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

    # fungsi untuk menerima streaming video
    def receive_video(self, stop_event, pipe_in, host_ip, video_port):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock_video:
            sock_video.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock_video.settimeout(.5)
            sock_video.bind((host_ip, video_port))
            data = bytearray(2048)
            while not stop_event.is_set():
                try:
                    size, addr = sock_video.recvfrom_into(data)
                    # logger.info({'action': 'receive_video', 'data': data})
                except socket.timeout as ex:
                    logger.warning({'action': 'receive_video', 'ex': ex })
                    time.sleep(0.5)
                    continue
                except socket.error as ex:
                    logger.error({'action': 'receive_video', 'ex': ex})
                    break
                try:
                    pipe_in.write(data[:size])
                    pipe_in.flush()
                except Exception as ex:
                    logger.error({'action': 'receive_video', 'ex': ex})
                    break

    def video_binary_generator(self):
        while True:
            try:
                frame = self.proc_stdout.read(FRAME_SIZE)
            except Exception as ex:
                logger.error({'action': 'video_binary_generator', 'ex': ex})
                continue

            if not frame:
                continue

            frame = np.fromstring(frame, np.uint8).reshape(FRAME_Y, FRAME_X, 3)
            yield frame

    def enable_face_detect(self):
        self._is_enable_face_detect = True

    def disable_face_detect(self):
        self._is_enable_face_detect = False

    def video_jpeg_generator(self):
        for frame in self.video_binary_generator():
            if self._is_enable_face_detect:
                if self.is_patrol:
                    self.stop_patrol()

                gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                for (x, y, w, h) in faces:
                    cv.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

                    # Inisiasi layer area tangkapan drone dan area jangkauan
                    face_center_x = x + (w/2)
                    face_center_y = y + (h/2)
                    diff_x = FRAME_CENTER_X - face_center_x
                    diff_y = FRAME_CENTER_Y - face_center_y
                    face_area = w * h
                    percent_face = face_area / FRAME_AREA

                    # Inisiasi jarak parameter drone saat mendeteksi wajah
                    drone_x, drone_y, drone_z, speed = 0, 0, 0, self.speed
                    if diff_x < -30:
                        drone_y = -30
                    if diff_x > 30:
                        drone_y = 30
                    if diff_y < -15:
                        drone_z = -30
                    if diff_y > 15:
                        drone_z = 30
                    if percent_face > 0.30:
                        drone_x = -30
                    if percent_face < 0.02:
                        drone_x = 30
                    self.send_command(f'go {drone_x} {drone_y} {drone_z} {speed}',
                                      blocking=False)
                    break

            _, jpeg = cv.imencode('.jpg', frame)
            jpeg_binary = jpeg.tobytes()
            yield jpeg_binary