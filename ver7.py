import cv2 as cv
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import pytesseract


# идет расшифровка только английского текста, в целом нормальнее стало
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class TopZoneCropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Сегментация и фильтрация областей с текстом (OCR)")
        self.root.geometry("1400x900")

        self.img_orig = None
        self.crop_top = None
        self.img_remainder = None
        self.crop_remainder_top25 = None
        self.figures_top25 = []
        self.figure_tk_images = []

        ctrl_frame = tk.Frame(root, bd=1, relief=tk.RAISED, padx=10, pady=10)
        ctrl_frame.pack(side=tk.TOP, fill=tk.X)

        self.btn_load = tk.Button(
            ctrl_frame,
            text="Выбрать изображение",
            command=self.load_image,
            font=("Arial", 10, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=10,
            pady=5
        )
        self.btn_load.pack(side=tk.LEFT, padx=10)

        # параметры поиска для верхней зоны
        tk.Label(ctrl_frame, text="Слияние зоны X:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(10, 2))
        self.scale_kernel_x = tk.Scale(
            ctrl_frame, from_=5, to=150, orient=tk.HORIZONTAL, length=100, command=lambda e: self.process_and_update()
        )
        self.scale_kernel_x.set(40)
        self.scale_kernel_x.pack(side=tk.LEFT, padx=2)

        tk.Label(ctrl_frame, text="Слияние зоны Y:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(10, 2))
        self.scale_kernel_y = tk.Scale(
            ctrl_frame, from_=5, to=150, orient=tk.HORIZONTAL, length=100, command=lambda e: self.process_and_update()
        )
        self.scale_kernel_y.set(30)
        self.scale_kernel_y.pack(side=tk.LEFT, padx=2)

        tk.Label(ctrl_frame, text="Мин. площадь зоны:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(10, 2))
        self.scale_min_area = tk.Scale(
            ctrl_frame, from_=500, to=50000, orient=tk.HORIZONTAL, length=100,
            command=lambda e: self.process_and_update()
        )
        self.scale_min_area.set(3000)
        self.scale_min_area.pack(side=tk.LEFT, padx=2)

        # дистанция слияния объектов
        tk.Label(ctrl_frame, text="Слияние объектов (px):", font=("Arial", 9, "bold"), fg="#0055B8").pack(
            side=tk.LEFT, padx=(15, 2))
        self.scale_fig_merge = tk.Scale(
            ctrl_frame, from_=0, to=60, orient=tk.HORIZONTAL, length=110, command=lambda e: self.process_and_update()
        )
        self.scale_fig_merge.set(15)
        self.scale_fig_merge.pack(side=tk.LEFT, padx=2)

        self.lbl_status = tk.Label(root, text="Выберите изображение", font=("Arial", 10, "italic"),
                                   fg="#333")
        self.lbl_status.pack(side=tk.TOP, fill=tk.X, pady=5)

        self.frame_images = tk.Frame(root)
        self.frame_images.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tk.Label(self.frame_images, text="1. Исходник / Половина", font=("Arial", 9, "bold")).grid(row=0, column=0,
                                                                                                   padx=2, pady=2)
        tk.Label(self.frame_images, text="2. Верхняя зона (Top Crop)", font=("Arial", 9, "bold")).grid(row=0, column=1,
                                                                                                       padx=2, pady=2)
        tk.Label(self.frame_images, text="3. Полный остаток", font=("Arial", 9, "bold")).grid(row=0, column=2, padx=2,
                                                                                              pady=2)

        self.lbl_col4_title = tk.Label(self.frame_images, text="4. 25% область (общая)", font=("Arial", 9, "bold"),
                                       fg="#0055B8")
        self.lbl_col4_title.grid(row=0, column=3, padx=2, pady=2)

        self.lbl_marked = tk.Label(self.frame_images, bg="#E0E0E0", text="Нет данных")
        self.lbl_marked.grid(row=1, column=0, sticky="nsew", padx=3, pady=5)

        self.lbl_top = tk.Label(self.frame_images, bg="#E0E0E0", text="Нет данных")
        self.lbl_top.grid(row=1, column=1, sticky="nsew", padx=3, pady=5)

        self.lbl_remainder = tk.Label(self.frame_images, bg="#E0E0E0", text="Нет данных")
        self.lbl_remainder.grid(row=1, column=2, sticky="nsew", padx=3, pady=5)

        self.lbl_top25 = tk.Label(self.frame_images, bg="#E0E0E0", text="Нет данных")
        self.lbl_top25.grid(row=1, column=3, sticky="nsew", padx=3, pady=5)

        for i in range(4):
            self.frame_images.columnconfigure(i, weight=1)
        self.frame_images.rowconfigure(1, weight=1)

        frame_figures_container = tk.LabelFrame(
            root,
            text=" Области с распознанным текстом ",
            font=("Arial", 10, "bold"),
            fg="#0055B8",
            bd=2
        )
        frame_figures_container.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)

        self.canvas_gallery = tk.Canvas(frame_figures_container, height=220, bg="#F5F5F5", highlightthickness=0)
        self.scrollbar_gallery = tk.Scrollbar(frame_figures_container, orient=tk.HORIZONTAL,
                                              command=self.canvas_gallery.xview)

        self.scrollable_gallery_frame = tk.Frame(self.canvas_gallery, bg="#F5F5F5")

        def _on_frame_configure(event):
            req_h = self.scrollable_gallery_frame.winfo_reqheight()
            if req_h > 0:
                self.canvas_gallery.config(height=max(180, req_h + 15), scrollregion=self.canvas_gallery.bbox("all"))

        self.scrollable_gallery_frame.bind("<Configure>", _on_frame_configure)

        self.canvas_gallery.create_window((0, 0), window=self.scrollable_gallery_frame, anchor="nw")
        self.canvas_gallery.configure(xscrollcommand=self.scrollbar_gallery.set)

        self.canvas_gallery.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=(5, 0))
        self.scrollbar_gallery.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        self.canvas_gallery.bind_all(
            "<Shift-MouseWheel>",
            lambda e: self.canvas_gallery.xview_scroll(int(-1 * (e.delta / 120)), "units")
        )

        self.tk_marked = None
        self.tk_top = None
        self.tk_remainder = None
        self.tk_top25 = None

    def trim_white_borders(self, img, threshold=245):
        if img is None or img.size == 0:
            return img

        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        binary_mask = (gray < threshold).astype(np.uint8) * 255

        denoised_kernel = cv.getStructuringElement(cv.MORPH_RECT, (3, 3))
        clean_mask = cv.morphologyEx(binary_mask, cv.MORPH_OPEN, denoised_kernel)

        coords = np.argwhere(clean_mask > 0)
        if coords.size == 0:
            coords = np.argwhere(binary_mask > 0)
            if coords.size == 0:
                return img

        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)

        return img[y_min:y_max + 1, x_min:x_max + 1]

    def remove_horizontal_lines(self, img, min_line_width=40):
        if img is None or img.size == 0:
            return img

        result = img.copy()
        gray = cv.cvtColor(result, cv.COLOR_BGR2GRAY)
        _, thresh = cv.threshold(gray, 220, 255, cv.THRESH_BINARY_INV)

        kernel = cv.getStructuringElement(cv.MORPH_RECT, (min_line_width, 1))
        horizontal_lines = cv.morphologyEx(thresh, cv.MORPH_OPEN, kernel)

        expand_kernel = cv.getStructuringElement(cv.MORPH_RECT, (1, 3))
        horizontal_lines = cv.dilate(horizontal_lines, expand_kernel, iterations=1)

        result[horizontal_lines == 255] = (255, 255, 255)
        return result

    def recognize_text(self, fig_crop):
        if fig_crop is None or fig_crop.size == 0:
            return None

        try:
            gray = cv.cvtColor(fig_crop, cv.COLOR_BGR2GRAY)

            h, w = gray.shape[:2]
            if h < 30 or w < 30:
                gray = cv.resize(gray, (w * 2, h * 2), interpolation=cv.INTER_CUBIC)

            text = pytesseract.image_to_string(gray, lang="eng", config="--psm 6")
            cleaned_text = text.strip()

            if cleaned_text and any(char.isalnum() for char in cleaned_text):
                return cleaned_text
            return None
        except Exception:
            return None

    def detect_and_extract_figures(self, img_25, min_fig_area=100, merge_dist=15):
        if img_25 is None or img_25.size == 0:
            return None, []

        annotated_img = img_25.copy()
        gray = cv.cvtColor(img_25, cv.COLOR_BGR2GRAY)
        _, thresh = cv.threshold(gray, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)

        if merge_dist > 0:
            kernel = cv.getStructuringElement(cv.MORPH_RECT, (merge_dist, merge_dist))
            merged_thresh = cv.dilate(thresh, kernel, iterations=1)
        else:
            merged_thresh = thresh

        contours, _ = cv.findContours(merged_thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        bounding_boxes = [cv.boundingRect(cnt) for cnt in contours]
        sorted_boxes = sorted(
            [b for b in bounding_boxes if b[2] * b[3] >= min_fig_area],
            key=lambda b: (b[1], b[0])
        )

        valid_items = []
        idx = 1

        for (x, y, w, h) in sorted_boxes:
            fig_crop = img_25[y:y + h, x:x + w]
            text = self.recognize_text(fig_crop)

            if text:
                valid_items.append((fig_crop, text))

                cv.rectangle(annotated_img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv.putText(
                    annotated_img, str(idx), (x, max(12, y - 3)),
                    cv.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1
                )
                idx += 1

        return annotated_img, valid_items

    def render_figures_gallery(self):
        for child in self.scrollable_gallery_frame.winfo_children():
            child.destroy()

        self.figure_tk_images.clear()

        if not self.figures_top25:
            lbl_empty = tk.Label(self.scrollable_gallery_frame, text="Текстовые области не найдены", bg="#F5F5F5",
                                 fg="#888")
            lbl_empty.pack(padx=20, pady=30)
            return

        for idx, (fig_crop, ocr_result) in enumerate(self.figures_top25, start=1):
            box_frame = tk.Frame(self.scrollable_gallery_frame, bd=1, relief=tk.SOLID, bg="white", padx=6, pady=6)
            box_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.Y)

            lbl_num = tk.Label(box_frame, text=f"№{idx}", font=("Arial", 8, "bold"), bg="white", fg="#0055B8")
            lbl_num.pack(side=tk.TOP)

            fig_rgb = cv.cvtColor(fig_crop, cv.COLOR_BGR2RGB)
            pil_img = Image.fromarray(fig_rgb)
            pil_img.thumbnail((140, 65), Image.Resampling.LANCZOS)

            tk_img = ImageTk.PhotoImage(pil_img)
            self.figure_tk_images.append(tk_img)

            lbl_img = tk.Label(box_frame, image=tk_img, bg="white")
            lbl_img.pack(side=tk.TOP, pady=2)

            h_f, w_f = fig_crop.shape[:2]
            lbl_size = tk.Label(box_frame, text=f"{w_f}x{h_f} px", font=("Arial", 7), bg="white", fg="#888")
            lbl_size.pack(side=tk.TOP)

            lbl_text_title = tk.Label(box_frame, text="Текст:", font=("Arial", 7, "bold"), bg="white", fg="#333")
            lbl_text_title.pack(side=tk.TOP, anchor="w", pady=(3, 0))

            lbl_ocr = tk.Label(
                box_frame,
                text=ocr_result,
                font=("Arial", 8),
                bg="#E8F0FE",
                fg="#1A73E8",
                wraplength=140,
                justify=tk.LEFT,
                bd=1,
                relief=tk.GROOVE,
                padx=4,
                pady=3
            )
            lbl_ocr.pack(side=tk.TOP, fill=tk.X, expand=True, pady=(2, 4))

        self.root.update_idletasks()
        self.canvas_gallery.configure(scrollregion=self.canvas_gallery.bbox("all"))

    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[
                ("Изображения", "*.png *.jpg *.jpeg"),
                ("Все файлы", "*.*")
            ]
        )
        if not file_path:
            return

        img_np = np.fromfile(file_path, dtype=np.uint8)
        loaded_img = cv.imdecode(img_np, cv.IMREAD_COLOR)

        if loaded_img is None:
            messagebox.showerror("Ошибка", "Не удалось открыть файл.")
            return

        h, w = loaded_img.shape[:2]
        if w > h:
            self.img_orig = loaded_img[:, :w // 2]
            status_prefix = f"Горизонтальное фото ({w}x{h}) -> Взята левая часть ({self.img_orig.shape[1]}x{h})."
        else:
            self.img_orig = loaded_img
            status_prefix = f"Вертикальное фото ({w}x{h})."

        self.process_and_update(status_prefix)

    def process_and_update(self, status_prefix=""):
        if self.img_orig is None:
            return

        gray = cv.cvtColor(self.img_orig, cv.COLOR_BGR2GRAY)
        _, thresh = cv.threshold(gray, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)

        kx = self.scale_kernel_x.get()
        ky = self.scale_kernel_y.get()
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (kx, ky))
        merged_mask = cv.morphologyEx(thresh, cv.MORPH_CLOSE, kernel)

        contours, _ = cv.findContours(merged_mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        min_area = self.scale_min_area.get()
        valid_zones = []

        for cnt in contours:
            area = cv.contourArea(cnt)
            if area >= min_area:
                x, y, w, h = cv.boundingRect(cnt)
                valid_zones.append((x, y, w, h, area))

        output_img = self.img_orig.copy()

        if valid_zones:
            valid_zones.sort(key=lambda z: z[1])
            tx, ty, tw, th, _ = valid_zones[0]

            self.crop_top = self.img_orig[ty:ty + th, tx:tx + tw]

            raw_remainder = self.img_orig[ty + th:, :]
            clean_remainder = self.remove_horizontal_lines(raw_remainder, min_line_width=40)
            self.img_remainder = self.trim_white_borders(clean_remainder, threshold=245)

            if self.img_remainder is not None and self.img_remainder.size > 0:
                h_rem = self.img_remainder.shape[0]
                slice_h = max(1, int(h_rem * 0.25))
                self.crop_remainder_top25 = self.img_remainder[:slice_h, :]

                fig_merge_dist = self.scale_fig_merge.get()
                annotated_top25, self.figures_top25 = self.detect_and_extract_figures(
                    self.crop_remainder_top25, min_fig_area=100, merge_dist=fig_merge_dist
                )
            else:
                self.crop_remainder_top25 = None
                annotated_top25, self.figures_top25 = None, []

            cv.rectangle(output_img, (tx, ty), (tx + tw, ty + th), (0, 255, 0), 3)

            text_count = len(self.figures_top25)
            self.lbl_col4_title.config(text=f"4. 25% область (С текстом: {text_count})")

            msg = f"{status_prefix} Областей с текстом: {text_count} шт." if status_prefix else f"Областей с текстом: {text_count} шт."
            self.lbl_status.config(text=msg)

            top_rgb = cv.cvtColor(self.crop_top, cv.COLOR_BGR2RGB)
            self.tk_top = ImageTk.PhotoImage(self.resize_for_preview(Image.fromarray(top_rgb)))
            self.lbl_top.config(image=self.tk_top, text="")

            if self.img_remainder is not None and self.img_remainder.size > 0:
                rem_rgb = cv.cvtColor(self.img_remainder, cv.COLOR_BGR2RGB)
                self.tk_remainder = ImageTk.PhotoImage(self.resize_for_preview(Image.fromarray(rem_rgb)))
                self.lbl_remainder.config(image=self.tk_remainder, text="")
            else:
                self.lbl_remainder.config(image=None, text="Пусто")

            if annotated_top25 is not None and annotated_top25.size > 0:
                top25_rgb = cv.cvtColor(annotated_top25, cv.COLOR_BGR2RGB)
                self.tk_top25 = ImageTk.PhotoImage(self.resize_for_preview(Image.fromarray(top25_rgb)))
                self.lbl_top25.config(image=self.tk_top25, text="")
            else:
                self.lbl_top25.config(image=None, text="Пусто")

        else:
            self.lbl_top.config(image=None, text="Зона не найдена")
            self.lbl_remainder.config(image=None, text="Зона не найдена")
            self.lbl_top25.config(image=None, text="Зона не найдена")
            self.figures_top25 = []
            self.lbl_status.config(text="Зоны не найдены. Уменьшить параметр 'Мин. площадь'.")

        marked_rgb = cv.cvtColor(output_img, cv.COLOR_BGR2RGB)
        self.tk_marked = ImageTk.PhotoImage(self.resize_for_preview(Image.fromarray(marked_rgb)))
        self.lbl_marked.config(image=self.tk_marked, text="")

        self.render_figures_gallery()

    def resize_for_preview(self, pil_img, max_size=(280, 380)):
        pil_img.thumbnail(max_size, Image.Resampling.LANCZOS)
        return pil_img


if __name__ == "__main__":
    root = tk.Tk()
    app = TopZoneCropApp(root)
    root.mainloop()