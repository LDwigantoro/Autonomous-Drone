# Autonomous Drone

Autonomous drone for my final bachelor thesis.

## Installation

Install and use this library [pip](https://github.com/damiafuentes/DJITelloPy/) to command tello drone.

```bash
pip install djitellopy
```

## Example

```python

from djitellopy import Tello

# inisiasi variabel dengan fungsi tello
tello = Tello()

# melakukan koneksi dan take off drone
tello.connect()
tello.takeoff()

# melakukan gerakan drone
tello.move_left(100)
tello.rotate_counter_clockwise(90)
tello.move_forward(100)

# drone mendarat
tello.land()
```
## Image Detection Using OpenCV

Using Haar Cascade Classifier To Detect Image

![detection_result](src\image_detection.PNG)

## Documentation

[DJITelloPy API Reference](https://djitellopy.readthedocs.io/en/latest/)

Created with ❤️ by Leonardo Dwigantoro
