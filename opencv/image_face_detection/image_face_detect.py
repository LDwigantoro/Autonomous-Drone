# import library
import cv2 as cv

# membuat cascade untuk wajah dan mata
# kode masih terdapat error saat mendeteksi wajah yang memakai kacamata
face_cascade = cv.CascadeClassifier('haarcascade_frontalface_default.xml')
eye_cascade = cv.CascadeClassifier('haarcascade_eye.xml')

# import foto yang akan dideteksi
img = cv.imread('image2.jpg')

# mengubah image ke grayscale
gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

# mendeteksi wajah di grayscale
# 1.3 = scale factor, berguna untuk mendeteksi wajah yang berukuran kecil diframe
# 5 = minNeigbhros, berguna untuk mendeteksi wajah yang overlapping
faces = face_cascade.detectMultiScale(gray, 1.3, 5)

# mencetak berapa jumlah wajah yang terdeteksi
print(len(faces))

# looping dalam koodinat x dan y dan juga weight dan height dalam faces
for (x, y, w, h) in faces:
    # mendeteksi wajah dalam kotak yang diberi warna biru
    # koodinat x dan y dimulai dari pojok kiri atas
    # x = koodirnat weight dari foto dimana semakin kekanan nilai semakin tinggi
    # y = koodirnat height dari foto dimana semakin kebawah nilai semakin tinggi
    # x+w = hasil dari deteksi wajah dalam horizontal
    # y+h = = hasil dari deteksi wajah dalam vertikal
    # (255, 0, 0), 2 = warna kotak yang mendeteksi wajah
    cv.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)

    # mengubah mata dalam faces menjadi grey agar bisa dideteksi
    eye_gray = gray[y:y+h, x:x+w]

    # memotong hanya bagian mata dalam faces
    eye_color = img[y:y+h, x:x+w]

    # mendeteksi mata dalam wajah
    eyes = eye_cascade.detectMultiScale(eye_gray)

    # looping dalam koodinat ex dan ey dan juga weight dan height dalam mata
    for (ex, ey, ew, eh) in eyes:
        # mendeteksi mata dalam kotak yang diberi warna hijau
        cv.rectangle(eye_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)

# melakukan output hasil
cv.imshow('img', img)
cv.waitKey(0)
cv.destroyAllWindows()
