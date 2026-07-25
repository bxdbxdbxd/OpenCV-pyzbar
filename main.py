import cv2
import numpy as np
from pyzbar.pyzbar import decode
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# для распознования штрихкода, иногда плохо определяет, но в целом нормально ~80%
def extract_and_decode_barcode(image_path: str):
    image = cv2.imread(image_path)
    if image is None:
        return None, []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    grad_x = cv2.Sobel(gray, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
    grad_y = cv2.Sobel(gray, ddepth=cv2.CV_32F, dx=0, dy=1, ksize=-1)
    gradient = cv2.subtract(grad_x, grad_y)
    gradient = cv2.convertScaleAbs(gradient)

    blurred = cv2.blur(gradient, (9, 9))
    _, thresh = cv2.threshold(blurred, 225, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    closed = cv2.erode(closed, None, iterations=4)
    closed = cv2.dilate(closed, None, iterations=4)

    contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    output_img = image.copy()
    roi = image
    bbox = None

    if contours:
        c = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)

        padding = 15
        img_h, img_w = image.shape[:2]
        x_start = max(0, x - padding)
        y_start = max(0, y - padding)
        x_end = min(img_w, x + w + padding)
        y_end = min(img_h, y + h + padding)

        roi = image[y_start:y_end, x_start:x_end]
        bbox = (x_start, y_start, x_end, y_end)

    decoded_objects = decode(roi)
    if not decoded_objects and contours:
        decoded_objects = decode(image)

    if bbox:
        cv2.rectangle(output_img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 3)

    results = []
    for obj in decoded_objects:
        results.append({
            "data": obj.data.decode("utf-8"),
            "type": obj.type
        })

    return output_img, results


class BarcodeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Детектор штрихкодов")
        self.root.geometry("700x650")
        self.root.configure(bg="#f0f0f0")

        self.btn_select = tk.Button(
            root,
            text="Выбрать изображение",
            command=self.select_image,
            font=("Arial", 12, "bold"),
            bg="#007bff",
            fg="white",
            padx=15,
            pady=8,
            relief="flat"
        )
        self.btn_select.pack(pady=15)

        self.image_label = tk.Label(root, text="Изображение не выбрано", bg="#e0e0e0", width=60, height=18)
        self.image_label.pack(pady=10, fill="both", expand=True)

        self.result_text = tk.Text(root, height=5, font=("Consolas", 11), wrap="word")
        self.result_text.pack(pady=15, padx=20, fill="x")

    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Выберите файл с штрихкодом",
            filetypes=[("Изображения", "*.jpg *.jpeg *.png *.bmp *.webp")]
        )

        if not file_path:
            return

        processed_img, barcodes = extract_and_decode_barcode(file_path)

        if processed_img is None:
            messagebox.showerror("Ошибка", "Не удалось загрузить изображение.")
            return

        self.display_image(processed_img)

        self.result_text.delete("1.0", tk.END)
        if barcodes:
            self.result_text.insert(tk.END, "НАЙДЕННЫЕ ШТРИХКОДЫ:\n")
            for i, b in enumerate(barcodes, 1):
                self.result_text.insert(tk.END, f"{i}. Тип: {b['type']} | Значение: {b['data']}\n")
        else:
            self.result_text.insert(tk.END, "Штрихкод не найден или не удалось расшифровать.")

    def display_image(self, cv2_img):
        rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)

        h, w, _ = rgb_img.shape
        max_size = 500

        scale = min(max_size / w, max_size / h)
        new_w, new_h = int(w * scale), int(h * scale)

        pil_img = Image.fromarray(rgb_img).resize((new_w, new_h), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(pil_img)

        self.image_label.configure(image=tk_img, text="")
        self.image_label.image = tk_img


if __name__ == "__main__":
    main_window = tk.Tk()
    app = BarcodeApp(main_window)
    main_window.mainloop()