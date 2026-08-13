import cv2 as cv
import numpy as np
import pytesseract
import re


pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class DesignAnalyzer:
    def __init__(self, kernel_x=40, kernel_y=30, min_area=3000, fig_merge_dist=15):
        self.kernel_x = kernel_x
        self.kernel_y = kernel_y
        self.min_area = min_area
        self.fig_merge_dist = fig_merge_dist

    def qimage_to_cv2(self, qimage):
        qimage = qimage.convertToFormat(qimage.Format.Format_RGB888)
        width = qimage.width()
        height = qimage.height()

        ptr = qimage.bits()
        ptr.setsize(qimage.sizeInBytes())

        bytes_per_line = qimage.bytesPerLine()
        arr = np.array(ptr).reshape((height, bytes_per_line))

        arr = arr[:, :width * 3]
        arr = arr.reshape((height, width, 3))

        return cv.cvtColor(arr, cv.COLOR_RGB2BGR)

    def get_rectangle_corners(self, box, offset_y=0):
        x, y, w, h = box
        global_y = y + offset_y
        return [
            (x, global_y),
            (x + w, global_y),
            (x + w, global_y + h),
            (x, global_y + h)
        ]

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
        return img[content_rows[0]:, :]

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
        return str(max(int(n) for n in nums))

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
            has_valid_color = any(t in valid_words or (t.isdigit() and 2 <= len(t) <= 4) for t in tokens)
            if has_valid_color and not any(bad in line_upper for bad in ["EPSIO", "БИОЙОГУРТ", "УПАКОВК"]):
                clean_lines.append(line_str)
        return ", ".join(clean_lines) if clean_lines else ""

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

            min_x = min(item['box'][0] for item in group)
            min_y = min(item['box'][1] for item in group)
            max_x = max(item['box'][0] + item['box'][2] for item in group)
            max_y = max(item['box'][1] + item['box'][3] for item in group)

            combined_crop = base_img[min_y:max_y, min_x:max_x]
            combined_text = "\n".join(item['text'] for item in group if item.get('text'))
            cleaned_colors = self.extract_colors_from_text(combined_text)

            if cleaned_colors:
                merged.append({
                    'box': (min_x, min_y, max_x - min_x, max_y - min_y),
                    'crop': combined_crop,
                    'text': combined_text,
                    'extracted_colors': cleaned_colors
                })
        return merged

    def find_design_for_cmyk(self, cmyk_item, design_candidates, img_w):
        cx, cy, cw, ch = cmyk_item['box']
        best_candidate = None
        min_score = float('inf')

        for design_item in design_candidates:
            if design_item is cmyk_item or design_item['box'] == cmyk_item['box']:
                continue
            dx, dy, dw, dh = design_item['box']
            if (dx + dw) > cx + 10:
                continue

            horizontal_distance = cx - (dx + dw)
            if horizontal_distance < -10 or horizontal_distance > 0.30 * img_w:
                continue

            vertical_overlap = min(cy + ch, dy + dh) - max(cy, dy)
            y_shift = abs((dy + dh / 2.0) - (cy + ch / 2.0))
            if vertical_overlap <= 0 and y_shift > max(1.2 * max(ch, dh), 30):
                continue

            if not self.extract_max_design_number(design_item['text']):
                continue

            score = max(0, horizontal_distance) + y_shift
            if score < min_score:
                min_score = score
                best_candidate = design_item

        return best_candidate

    def filter_and_link_pairs(self, items, img_w, base_img):
        exclude_words = {"БИОЙОГУРТ", "ЙОГУРТ", "КОКТЕЙЛЬ", "МОЛОКО", "%", "ПЕРСИКОМ", "МАССА", "СОСТАВ"}
        color_keywords = ["YELLOW", "YELIOW", "MAGENTA", "CYAN", "BLACK", "PANTONE", "ЛАК", "LAK", "VARNISH"]

        raw_cmyk_candidates = []
        design_candidates = []

        for item in items:
            x, y, w, h = item['box']
            text_upper = (item['text'] or "").upper()
            if w > 0.25 * img_w or any(w_ex in text_upper for w_ex in exclude_words):
                continue

            if self.extract_max_design_number(item['text']):
                design_candidates.append(item)

            if any(ck in text_upper for ck in color_keywords) or any(
                    t in {"C", "M", "Y", "K"} for t in re.findall(r'[A-ZА-Я0-9]+', text_upper)):
                extracted = self.extract_colors_from_text(item['text'])
                if extracted:
                    item['extracted_colors'] = extracted
                    raw_cmyk_candidates.append(item)

        merged_cmyk = self.merge_nearby_cmyk_blocks(raw_cmyk_candidates, base_img, img_w)
        results = []
        used_design_ids = set()

        for c_item in merged_cmyk:
            best_d_item = self.find_design_for_cmyk(c_item, design_candidates, img_w)
            if best_d_item is not None:
                d_id = id(best_d_item)
                if d_id in used_design_ids:
                    continue
                used_design_ids.add(d_id)

                results.append({
                    'design_num': self.extract_max_design_number(best_d_item['text']),
                    'colors': c_item['extracted_colors'],
                    'cmyk_box': c_item['box'],
                    'design_box': best_d_item['box']
                })
        return results

    def process_image(self, input_source):
        if isinstance(input_source, str):
            img_np = np.fromfile(input_source, dtype=np.uint8)
            working_img = cv.imdecode(img_np, cv.IMREAD_COLOR)
        elif str(type(input_source)).find('QImage') != -1:
            working_img = self.qimage_to_cv2(input_source)
        elif isinstance(input_source, np.ndarray):
            working_img = input_source.copy()
        else:
            raise ValueError("Неподдерживаемый формат входных данных")

        if working_img is None or working_img.size == 0:
            return []

        h, w = working_img.shape[:2]
        if w > h:
            working_img = working_img[:, :w // 2]

        working_img = self.trim_top_white_space(working_img, threshold=240)
        gray = cv.cvtColor(working_img, cv.COLOR_BGR2GRAY)
        _, thresh = cv.threshold(gray, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)

        kernel = cv.getStructuringElement(cv.MORPH_RECT, (self.kernel_x, self.kernel_y))
        merged_mask = cv.morphologyEx(thresh, cv.MORPH_CLOSE, kernel)
        contours, _ = cv.findContours(merged_mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        valid_zones = [(cv.boundingRect(c)[0], cv.boundingRect(c)[1], cv.boundingRect(c)[2], cv.boundingRect(c)[3])
                       for c in contours if cv.contourArea(c) >= self.min_area]

        if not valid_zones:
            return []

        valid_zones.sort(key=lambda z: z[1])
        tx, ty, tw, th = valid_zones[0]

        raw_remainder = working_img[ty + th:, :]
        clean_remainder = self.remove_horizontal_lines(raw_remainder, min_line_width=40)
        trimmed_remainder = self.trim_white_borders(clean_remainder, threshold=245)

        if trimmed_remainder is None or trimmed_remainder.size == 0:
            return []

        rem_gray = cv.cvtColor(clean_remainder, cv.COLOR_BGR2GRAY)
        rem_bin = (rem_gray < 245).astype(np.uint8) * 255
        rem_coords = np.argwhere(rem_bin > 0)
        trim_offset_y = rem_coords.min(axis=0)[0] if rem_coords.size > 0 else 0
        current_offset_y = ty + th + trim_offset_y

        h_rem = trimmed_remainder.shape[0]
        crop_remainder_top25 = trimmed_remainder[:max(1, int(h_rem * 0.25)), :]

        img_25 = crop_remainder_top25
        min_ch = np.min(img_25, axis=2)
        _, thresh_25 = cv.threshold(min_ch, 0, 255, cv.THRESH_BINARY_INV + cv.THRESH_OTSU)

        m_kernel = cv.getStructuringElement(cv.MORPH_RECT, (self.fig_merge_dist, self.fig_merge_dist))
        merged_thresh_25 = cv.dilate(thresh_25, m_kernel, iterations=1) if self.fig_merge_dist > 0 else thresh_25

        contours_25, _ = cv.findContours(merged_thresh_25, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        main_boxes = [cv.boundingRect(cnt) for cnt in contours_25 if
                      cv.boundingRect(cnt)[2] * cv.boundingRect(cnt)[3] >= 100]

        raw_items = []
        for bx, by, bw, bh in main_boxes:
            fig_crop = img_25[by:by + bh, bx:bx + bw]
            text = self.recognize_text(fig_crop)
            if text:
                raw_items.append({'crop': fig_crop, 'text': text, 'box': (bx, by, bw, bh)})

        valid_pairs = self.filter_and_link_pairs(raw_items, img_25.shape[1], img_25)

        final_output = []
        for pair in valid_pairs:
            final_output.append({
                "design_number": pair['design_num'],
                "colors": pair['colors'],
                "coordinates": {
                    "cmyk_box": self.get_rectangle_corners(pair['cmyk_box'], current_offset_y),
                    "design_box": self.get_rectangle_corners(pair['design_box'], current_offset_y)
                }
            })

        return final_output