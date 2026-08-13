import cv2
from pyzbar import pyzbar
import numpy as np


def extract_ean13(image_path: str) -> str | None:
    try:
        with open(image_path, "rb") as f:
            chunk = f.read()
        image = cv2.imdecode(np.frombuffer(chunk, np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        image = None

    if image is None:
        print(f"Не удалось загрузить изображение по пути: {image_path}")
        return None

    barcodes = pyzbar.decode(image)

    if not barcodes:
        print("Штрихкоды на изображении не найдены.")
        return None

    target_barcode = None

    for barcode in barcodes:
        barcode_type = barcode.type
        barcode_data = barcode.data.decode("utf-8")

        if barcode_type == "EAN13":
            target_barcode = barcode_data
            (x, y, w, h) = barcode.rect
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 3)

            text = f"{barcode_data} ({barcode_type})"
            cv2.putText(image, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            print(f"Найден EAN13: {barcode_data}")
            break

    if not target_barcode:
        print("На картинке есть штрихкоды, но среди них нет типа EAN13.")
        return None

    return target_barcode

# Просто пример использование ну и проверка работы
if __name__ == "__main__":
    result = extract_ean13(r"C:\Users\tempt\Downloads\дизайны\4444.jpg")
    print(f"Результат функции: {result}")