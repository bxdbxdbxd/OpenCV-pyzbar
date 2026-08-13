import cv2 as cv
import numpy as np
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def recognize_text_tesseract(fig_crop):
    if fig_crop is None or fig_crop.size == 0:
        return None

    try:
        h, w = fig_crop.shape[:2]
        scale = max(2.5, 60.0 / min(h, w)) if min(h, w) < 30 else 1.0

        min_ch = np.min(fig_crop, axis=2)
        if scale > 1.0:
            min_ch = cv.resize(min_ch, (int(w * scale), int(h * scale)), interpolation=cv.INTER_CUBIC)

        _, thresh_min = cv.threshold(min_ch, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
        text_min = pytesseract.image_to_string(thresh_min, lang="eng", config="--psm 6").strip()
        if text_min and any(char.isalnum() for char in text_min):
            return text_min

        gray = cv.cvtColor(fig_crop, cv.COLOR_BGR2GRAY)
        if scale > 1.0:
            gray = cv.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv.INTER_CUBIC)

        text_gray = pytesseract.image_to_string(gray, lang="eng", config="--psm 6").strip()
        if text_gray and any(char.isalnum() for char in text_gray):
            return text_gray

        return None
    except Exception:
        return None


if __name__ == "__main__":
    image_path = "1.jpg"

    img_np = np.fromfile(image_path, dtype=np.uint8)
    image = cv.imdecode(img_np, cv.IMREAD_COLOR)

    if image is not None:
        result_text = recognize_text_tesseract(image)

        print("Результат распознавания:")
        print(result_text if result_text else "Текст не найден")
    else:
        print("Не удалось загрузить изображение. Проверьте путь к файлу.")