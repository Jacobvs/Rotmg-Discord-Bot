import cv2
from pytesseract import pytesseract

img = cv2.imopen("who.png")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
cv2.imshow(gray)
blur = cv2.medianBlur(gray, 5)
cv2.imshow(blur)
thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
cv2.imshow(thresh)

# Morph open to remove noise and invert image
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
invert = 255 - opening
cv2.imshow(invert)
str = pytesseract.image_to_string(invert)
str = str.replace("\n", " ")
print(str)