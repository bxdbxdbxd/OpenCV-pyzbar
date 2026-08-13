import cv2 as cv
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import pytesseract
import math
import re

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class TopZoneCropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Прога")
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

        tk.Label(ctrl_frame, text="Слияние объектов (px):", font=("Arial", 9, "bold"), fg="#0055B8").pack(
            side=tk.LEFT, padx=(15, 2))
        self.scale_fig_merge = tk.Scale(
            ctrl_frame, from_=0, to=60, orient=tk.HORIZONTAL, length=110, command=lambda e: self.process_and_update()
        )
        self.scale_fig_merge.set(15)
        self.scale_fig_merge.pack(side=tk.LEFT, padx=2)

        self.lbl_status = tk.Label(root, text="Выберите изображение", font=("Arial", 10, "italic"), fg="#333")
        self.lbl_status.pack(side=tk.TOP, fill=tk.X, pady=5)

        self.frame_images = tk.Frame(root)
        self.frame_images.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tk.Label(self.frame_images, text="Исходник", font=("Arial", 9, "bold")).grid(row=0, column=0, padx=2, pady=2)
        tk.Label(self.frame_images, text="Верхняя зона", font=("Arial", 9, "bold")).grid(row=0, column=1, padx=2, pady=2)
        tk.Label(self.frame_images, text="Остаток", font=("Arial", 9, "bold")).grid(row=0, column=2, padx=2, pady=2)

        self.lbl_col4_title = tk.Label(self.frame_images, text="Результат", font=("Arial", 9, "bold"), fg="#0055B8")
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
            text=" Результаты ",
            font=("Arial", 10, "bold"),
            fg="#0055B8",
            bd=2
        )
        frame_figures_container.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)

        self.canvas_gallery = tk.Canvas(frame_figures_container, height=220, bg="#F5F5F5", highlightthickness=0)
        self.scrollbar_gallery = tk.Scrollbar(frame_figures_container, orient=tk.HORIZONTAL, command=self.canvas_gallery.xview)

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

    def trim_top_white_space(self, img, threshold=240):
        if img is None or img.size == 0:
            return img

        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]

        has_content = np.logical_or(gray < threshold, sat > 30).any(axis=1)
        content_rows = np.where(has_content)[0]

        if len(content_rows) == 0:
            return img

        top_y = content_rows[0]
        return img[top_y:, :]

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
            h, w = fig_crop.shape[:2]
            scale = max(2.5, 60.0 / min(h, w)) if min(h, w) < 30 else 1.0

            min_ch = np.min(fig_crop, axis=2)
            if scale > 1.0:
                min_ch = cv.resize(min_ch, (int(w * scale), int(h * scale)), interpolation=cv.INTER_CUBIC)

            _, thresh_min = cv.threshold(min_ch, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
            text_min = pytesseract.image_to_string(thresh_min, lang="eng+rus", config="--psm 6").strip()
            if text_min and any(char.isalnum() for char in text_min):
                return text_min

            gray = cv.cvtColor(fig_crop, cv.COLOR_BGR2GRAY)
            if scale > 1.0:
                gray = cv.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv.INTER_CUBIC)

            text_gray = pytesseract.image_to_string(gray, lang="eng+rus", config="--psm 6").strip()
            if text_gray and any(char.isalnum() for char in text_gray):
                return text_gray

            return None
        except Exception:
            return None

    def extract_max_design_number(self, text):
        if not text:
            return None
        nums = re.findall(r'(?<!\d)\d{8}(?!\d)', text)
        if not nums:
            return None
        max_val = max(int(n) for n in nums)
        return str(max_val)

    def extract_colors_from_text(self, text):
        if not text:
            return ""

        valid_words = {
            "YELLOW", "YELIOW", "MAGENTA", "CYAN", "BLACK", "PANTONE",
            "ЛАК", "LAK", "VARNISH", "WHITE", "БЕЛЫЙ", "C", "M", "Y", "K", "К", "С", "М"
        }

        clean_lines = []
        for line in text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            line_upper = line_str.upper()
            tokens = re.findall(r'[A-ZА-Я0-9]+', line_upper)

            has_valid_color = False
            for t in tokens:
                if t in valid_words or (t.isdigit() and 2 <= len(t) <= 4):
                    has_valid_color = True
                    break

            if has_valid_color and not any(bad in line_upper for bad in ["EPSIO", "БИОЙОГУРТ", "УПАКОВК"]):
                clean_lines.append(line_str)

        if clean_lines:
            return ", ".join(clean_lines)
        return ""

    def merge_nearby_cmyk_blocks(self, cmyk_items, base_img, img_w):
        if not cmyk_items:
            return []

        max_merged_w = min(0.18 * img_w, 220)

        merged = []
        visited = [False] * len(cmyk_items)

        for i in range(len(cmyk_items)):
            if visited[i]:
                continue

            group = [cmyk_items[i]]
            visited[i] = True

            changed = True
            while changed:
                changed = False
                for j in range(len(cmyk_items)):
                    if visited[j]:
                        continue

                    item_j = cmyk_items[j]
                    xj, yj, wj, hj = item_j['box']

                    test_min_x = min(min(item['box'][0] for item in group), xj)
                    test_max_x = max(max(item['box'][0] + item['box'][2] for item in group), xj + wj)
                    if (test_max_x - test_min_x) > max_merged_w:
                        continue

                    for g_item in group:
                        xg, yg, wg, hg = g_item['box']

                        x_overlap = max(0, min(xg + wg, xj + wj) - max(xg, xj))
                        v_gap = max(0, max(yg, yj) - min(yg + hg, yj + hj))
                        max_allowed_v_gap = min(2.0 * max(hg, hj), 25)

                        if (x_overlap > 0.3 * min(wg, wj) or abs(xg - xj) < 15) and v_gap <= max_allowed_v_gap:
                            group.append(item_j)
                            visited[j] = True
                            changed = True
                            break

                        y_overlap = max(0, min(yg + hg, yj + hj) - max(yg, yj))
                        h_gap = max(0, max(xg, xj) - min(xg + wg, xj + wj))
                        max_allowed_h_gap = min(1.5 * max(hg, hj), 30)

                        if y_overlap > 0.3 * min(hg, hj) and h_gap <= max_allowed_h_gap:
                            group.append(item_j)
                            visited[j] = True
                            changed = True
                            break

            min_x = min(item['box'][0] for item in group)
            min_y = min(item['box'][1] for item in group)
            max_x = max(item['box'][0] + item['box'][2] for item in group)
            max_y = max(item['box'][1] + item['box'][3] for item in group)

            combined_w = max_x - min_x
            combined_h = max_y - min_y
            combined_crop = base_img[min_y:max_y, min_x:max_x]
            combined_text = "\n".join(item['text'] for item in group if item.get('text'))
            cleaned_colors = self.extract_colors_from_text(combined_text)

            if cleaned_colors:
                merged.append({
                    'box': (min_x, min_y, combined_w, combined_h),
                    'crop': combined_crop,
                    'text': combined_text,
                    'extracted_colors': cleaned_colors
                })

        return merged

    def find_design_for_cmyk(self, cmyk_item, design_candidates, img_w):
        cx, cy, cw, ch = cmyk_item['box']

        cmyk_left = cx
        cmyk_top = cy
        cmyk_bottom = cy + ch
        cmyk_center_y = cy + ch / 2.0

        best_candidate = None
        min_score = float('inf')

        for design_item in design_candidates:
            if design_item is cmyk_item or design_item['box'] == cmyk_item['box']:
                continue

            dx, dy, dw, dh = design_item['box']
            design_right = dx + dw
            design_center_y = dy + dh / 2.0

            if design_right > cmyk_left + 10:
                continue

            horizontal_distance = cmyk_left - design_right
            if horizontal_distance < -10 or horizontal_distance > 0.30 * img_w:
                continue

            vertical_overlap = min(cmyk_bottom, dy + dh) - max(cmyk_top, dy)
            max_y_shift = max(1.2 * max(ch, dh), 30)
            y_shift = abs(design_center_y - cmyk_center_y)

            if vertical_overlap <= 0 and y_shift > max_y_shift:
                continue

            design_num = self.extract_max_design_number(design_item['text'])
            if not design_num:
                continue

            score = max(0, horizontal_distance) + y_shift

            if score < min_score:
                min_score = score
                best_candidate = design_item

        return best_candidate

    def filter_and_link_pairs(self, items, img_w, base_img):
        exclude_words = {
            "БИОЙОГУРТ", "ЙОГУРТ", "КОКТЕЙЛЬ", "МОЛОКО", "%", "ПЕРСИКОМ",
            "МАССА", "СОСТАВ", "ПРОИЗВОДИТЕЛЬ", "ДЕТЕЙ", "ДОШКОЛЬНОГО",
            "ШКОЛЬНОГО", "ВОЗРАСТА", "ПИТАНИЯ", "ДАТА", "ГОДЕН", "УПАКОВК"
        }
        color_keywords = ["YELLOW", "YELIOW", "MAGENTA", "CYAN", "BLACK", "PANTONE", "ЛАК", "LAK", "VARNISH"]

        raw_cmyk_candidates = []
        design_candidates = []

        for item in items:
            x, y, w, h = item['box']
            text = item['text'] if item['text'] else ""
            text_upper = text.upper()

            if w > 0.25 * img_w:
                continue

            if any(w_ex in text_upper for w_ex in exclude_words):
                continue

            max_num_str = self.extract_max_design_number(text)

            if max_num_str:
                design_candidates.append(item)

            has_full_color_word = any(ck in text_upper for ck in color_keywords)

            tokens = re.findall(r'[A-ZА-Я0-9]+', text_upper)
            has_color_token = False
            for t in tokens:
                if t in {"YELLOW", "MAGENTA", "CYAN", "BLACK", "PANTONE", "ЛАК", "VARNISH", "C", "M", "Y", "K", "К", "С", "М"}:
                    has_color_token = True
                    break
                if t.isdigit() and 2 <= len(t) <= 4 and not max_num_str:
                    has_color_token = True
                    break

            if (has_full_color_word or has_color_token) and (not max_num_str or has_full_color_word):
                extracted = self.extract_colors_from_text(text)
                if extracted:
                    item['extracted_colors'] = extracted
                    raw_cmyk_candidates.append(item)

        merged_cmyk_candidates = self.merge_nearby_cmyk_blocks(raw_cmyk_candidates, base_img, img_w)

        results = []
        used_design_ids = set()

        for c_item in merged_cmyk_candidates:
            best_d_item = self.find_design_for_cmyk(c_item, design_candidates, img_w)

            if best_d_item is not None:
                d_id = id(best_d_item)
                if d_id in used_design_ids:
                    continue

                used_design_ids.add(d_id)
                design_num = self.extract_max_design_number(best_d_item['text'])

                results.append({
                    'design_num': design_num,
                    'colors': c_item['extracted_colors'],
                    'cmyk_crop': c_item['crop'],
                    'design_crop': best_d_item['crop'],
                    'cmyk_box': c_item['box'],
                    'design_box': best_d_item['box']
                })

        return results

    def detect_and_extract_figures(self, img_25, min_fig_area=100, merge_dist=15):
        if img_25 is None or img_25.size == 0:
            return None, []

        annotated_img = img_25.copy()
        img_h, img_w = img_25.shape[:2]

        min_ch = np.min(img_25, axis=2)
        _, thresh = cv.threshold(min_ch, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)

        if merge_dist > 0:
            kernel = cv.getStructuringElement(cv.MORPH_RECT, (merge_dist, merge_dist))
            merged_thresh = cv.dilate(thresh, kernel, iterations=1)
        else:
            merged_thresh = thresh

        contours, _ = cv.findContours(merged_thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        main_boxes = [cv.boundingRect(cnt) for cnt in contours if cv.boundingRect(cnt)[2] * cv.boundingRect(cnt)[3] >= min_fig_area]

        raw_items = []
        for x, y, w, h in main_boxes:
            fig_crop = img_25[y:y + h, x:x + w]
            text = self.recognize_text(fig_crop)

            if text:
                raw_items.append({
                    'crop': fig_crop,
                    'text': text,
                    'box': (x, y, w, h)
                })

        valid_pairs = self.filter_and_link_pairs(raw_items, img_w, img_25)

        for idx, pair in enumerate(valid_pairs, start=1):
            cx, cy, cw, ch = pair['cmyk_box']
            cv.rectangle(annotated_img, (cx, cy), (cx + cw, cy + ch), (0, 255, 255), 2)

            dx, dy, dw, dh = pair['design_box']
            cv.rectangle(annotated_img, (dx, dy), (dx + dw, dy + dh), (255, 0, 0), 2)

            cv.putText(
                annotated_img, f"{pair['design_num']}", (cx, max(12, cy - 3)),
                cv.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1
            )

        return annotated_img, valid_pairs

    def render_figures_gallery(self):
        for child in self.scrollable_gallery_frame.winfo_children():
            child.destroy()

        self.figure_tk_images.clear()

        if not self.figures_top25:
            lbl_empty = tk.Label(
                self.scrollable_gallery_frame,
                text="Служебная маркировка не найдена",
                bg="#F5F5F5",
                fg="#888"
            )
            lbl_empty.pack(padx=20, pady=30)
            return

        for idx, pair in enumerate(self.figures_top25, start=1):
            box_frame = tk.Frame(self.scrollable_gallery_frame, bd=1, relief=tk.SOLID, bg="white", padx=8, pady=6)
            box_frame.pack(side=tk.LEFT, padx=8, pady=5, fill=tk.Y)

            lbl_design = tk.Label(
                box_frame,
                text=f"Номер дизайна: {pair['design_num']}",
                font=("Arial", 9, "bold"),
                bg="white",
                fg="#0055B8"
            )
            lbl_design.pack(side=tk.TOP, anchor="w")

            lbl_colors = tk.Label(
                box_frame,
                text=f"Цвета: {pair['colors']}",
                font=("Arial", 8, "bold"),
                bg="white",
                fg="#D81B60"
            )
            lbl_colors.pack(side=tk.TOP, anchor="w", pady=(2, 6))

            imgs_frame = tk.Frame(box_frame, bg="white")
            imgs_frame.pack(side=tk.TOP, fill=tk.X, expand=True)

            f_cmyk = tk.Frame(imgs_frame, bg="#F9F9F9", bd=1, relief=tk.GROOVE, padx=4, pady=4)
            f_cmyk.pack(side=tk.LEFT, padx=3)
            tk.Label(f_cmyk, text="Цвета", font=("Arial", 7, "bold"), bg="#F9F9F9", fg="#555").pack(side=tk.TOP)

            pil_cmyk = Image.fromarray(cv.cvtColor(pair['cmyk_crop'], cv.COLOR_BGR2RGB))
            pil_cmyk.thumbnail((120, 80), Image.Resampling.LANCZOS)
            tk_cmyk = ImageTk.PhotoImage(pil_cmyk)
            self.figure_tk_images.append(tk_cmyk)

            lbl_img_cmyk = tk.Label(f_cmyk, image=tk_cmyk, bg="white")
            lbl_img_cmyk.pack(side=tk.TOP, pady=2)

            f_design = tk.Frame(imgs_frame, bg="#F9F9F9", bd=1, relief=tk.GROOVE, padx=4, pady=4)
            f_design.pack(side=tk.LEFT, padx=3)
            tk.Label(f_design, text="Номер дизайна", font=("Arial", 7, "bold"), bg="#F9F9F9", fg="#555").pack(side=tk.TOP)

            pil_design = Image.fromarray(cv.cvtColor(pair['design_crop'], cv.COLOR_BGR2RGB))
            pil_design.thumbnail((120, 80), Image.Resampling.LANCZOS)
            tk_design = ImageTk.PhotoImage(pil_design)
            self.figure_tk_images.append(tk_design)

            lbl_img_design = tk.Label(f_design, image=tk_design, bg="white")
            lbl_img_design.pack(side=tk.TOP, pady=2)

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
            status_prefix = f"Горизонтальное фото ({w}x{h})."
        else:
            self.img_orig = loaded_img
            status_prefix = f"Вертикальное фото ({w}x{h})."

        self.process_and_update(status_prefix)

    def process_and_update(self, status_prefix=""):
        if self.img_orig is None:
            return

        working_img = self.trim_top_white_space(self.img_orig, threshold=240)

        gray = cv.cvtColor(working_img, cv.COLOR_BGR2GRAY)
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

        output_img = working_img.copy()

        if valid_zones:
            valid_zones.sort(key=lambda z: z[1])
            tx, ty, tw, th, _ = valid_zones[0]

            self.crop_top = working_img[ty:ty + th, tx:tx + tw]

            raw_remainder = working_img[ty + th:, :]
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
            self.lbl_col4_title.config(text="Результат")

            msg = f"Найдено: {text_count} шт."
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