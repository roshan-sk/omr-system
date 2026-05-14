import cv2
import numpy as np
import json

LETTERS = [chr(i) for i in range(ord('A'), ord('Z')+1)]
DIGITS  = "0123456789"
OPTIONS = "ABCDE"

LEVEL_OPTIONS = ["Lower Primary", "Upper Primary", "Junior",
                 "Intermediate", "Senior", "Open"]

NUM_ANSWER_GROUPS = 4
ROWS_PER_GROUP = 10
OPTIONS_PER_QUESTION = 5
CLUSTER_GAP = 18
DOB_MAX_GRID_DIST = 16

HOUGH_DP = 1.2
HOUGH_MIN_DIST = 14
HOUGH_PARAM1 = 50
HOUGH_PARAM2 = 18
HOUGH_MIN_R = 8
HOUGH_MAX_R = 18

MIN_HORIZ_LINES = 5
MAX_SKEW_DEG = 3.0

_LEVEL_Y1, _LEVEL_Y2 = 0.120, 0.168
_LEVEL_X1, _LEVEL_X2 = 0.01,  0.99


def _clamp(v, lo, hi):
    return max(lo, min(v, hi))

def _cluster_centers(values, gap=CLUSTER_GAP):
    if not values:
        return []
    arr = np.array(sorted(set(int(v) for v in values)))
    if len(arr) == 0:
        return []
    centers, cur = [], [arr[0]]
    for v in arr[1:]:
        if v - cur[-1] > gap:
            centers.append(int(np.median(cur)))
            cur = [v]
        else:
            cur.append(v)
    centers.append(int(np.median(cur)))
    return centers

def _detect_circles(gray):
    try:
        cs = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT,
                              dp=HOUGH_DP, minDist=HOUGH_MIN_DIST,
                              param1=HOUGH_PARAM1, param2=HOUGH_PARAM2,
                              minRadius=HOUGH_MIN_R, maxRadius=HOUGH_MAX_R)
        return np.round(cs[0]).astype(int) if cs is not None else None
    except Exception:
        return None

def _bubble_darkness(gray, bx, by, br, margin=2):
    try:
        patch = gray[max(0, by-br+margin):by+br-margin,
                     max(0, bx-br+margin):bx+br-margin]
        return float(255 - np.mean(patch)) if patch.size > 0 else 0.0
    except Exception:
        return 0.0

def _bubble_darkness_at(gray, x, y, r=10, margin=2):
    return _bubble_darkness(gray, x, y, r, margin)

def _closest_x(circles, target_x):
    best, best_d = None, float("inf")
    for c in circles:
        d = abs(int(c[0]) - target_x)
        if d < best_d:
            best_d, best = d, c
    return best

def _closest_xy(circles, tx, ty):
    best, best_d = None, float("inf")
    for c in circles:
        d = (int(c[0])-tx)**2 + (int(c[1])-ty)**2
        if d < best_d:
            best_d, best = d, c
    return best, best_d

def _find_adaptive_threshold(all_scores):
    if not all_scores:
        return 50.0
    arr = np.array(sorted(all_scores))
    if len(arr) < 2:
        return 50.0
    gaps = [(arr[i+1]-arr[i], float((arr[i]+arr[i+1])/2)) for i in range(len(arr)-1)]
    if not gaps:
        return 50.0
    best_gap, best_mid = max(gaps, key=lambda x: x[0])
    return best_mid if best_gap > 10 else 50.0

def _classify_bubble(scores, threshold):
    if not scores:
        return "EMPTY", None
    filled = [i for i, s in enumerate(scores) if s >= threshold]
    if len(filled) == 0:
        return "EMPTY", None
    if len(filled) == 1:
        return "OK", OPTIONS[filled[0]]
    return "MULTIPLE", [OPTIONS[i] for i in filled]

def _top_two_scores(scores):
    if not scores:
        return 0, 0.0, 0.0
    s = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    first = s[0]
    second = s[1] if len(s) > 1 else (0, 0.0)
    return first[0], first[1], second[1]


def auto_straighten(image):
    try:
        gray  = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        lines = cv2.HoughLines(cv2.Canny(gray, 50, 150), 1, np.pi/180, 200)
        if lines is None:
            return image
        horiz = [a for a in [(l[0][1]*180/np.pi)-90 for l in lines[:50]] if abs(a) < MAX_SKEW_DEG]
        if len(horiz) < MIN_HORIZ_LINES:
            return image
        angle = float(np.median(horiz))
        if abs(angle) < 0.1:
            return image
        M = cv2.getRotationMatrix2D((image.shape[1]//2, image.shape[0]//2), angle, 1)
        return cv2.warpAffine(image, M, (image.shape[1], image.shape[0]), borderMode=cv2.BORDER_REPLICATE)
    except Exception:
        return image


def detect_level(image):
    try:
        h, w   = image.shape[:2]
        strip  = image[int(_LEVEL_Y1*h):int(_LEVEL_Y2*h), int(_LEVEL_X1*w):int(_LEVEL_X2*w)]
        gray   = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
        sw     = strip.shape[1]
        sec_w  = sw / 6.0 if sw > 0 else 1.0

        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        _, _, stats, _ = cv2.connectedComponentsWithStats(bw)
        scores = [0.0] * 6
        for i in range(1, len(stats)):
            area = stats[i, cv2.CC_STAT_AREA]
            cx = stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH]//2
            cw = stats[i, cv2.CC_STAT_WIDTH]
            ch = stats[i, cv2.CC_STAT_HEIGHT]
            if not (60 < area < 700 and 8 < cw < 35 and 8 < ch < 35):
                continue
            asp = min(cw, ch) / max(cw, ch)
            if asp < 0.45:
                continue
            sec = min(5, int(cx / sec_w))
            s = area * asp
            if s > scores[sec]:
                scores[sec] = s
        top2 = sorted(scores, reverse=True)
        if top2[0] > 60 and (top2[0]-top2[1]) > 25:
            return LEVEL_OPTIONS[int(np.argmax(scores))]

        darkness = [0.0] * 6
        for p2 in [18, 15, 12, 10]:
            cs = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=50,
                                  param1=50, param2=p2, minRadius=7, maxRadius=16)
            if cs is None:
                continue
            cs = np.round(cs[0]).astype(int)
            sd = [0.0] * 6
            for c in cs:
                bx, by, br = int(c[0]), int(c[1]), int(c[2])
                patch = gray[max(0,by-br+2):by+br-2, max(0,bx-br+2):bx+br-2]
                d = float(255-np.mean(patch)) if patch.size > 0 else 0.0
                sec = min(5, int(bx/sec_w))
                if d > sd[sec]: sd[sec] = d
            t2 = sorted(sd, reverse=True)
            if t2[0] > 50 and (t2[0]-t2[1]) > 15:
                darkness = sd
                break
        ht2 = sorted(darkness, reverse=True)
        if ht2[0] > 50 and (ht2[0]-ht2[1]) > 15:
            return LEVEL_OPTIONS[int(np.argmax(darkness))]

        r  = 10
        sh = strip.shape[0]
        px = [255-float(np.mean(gray[max(0,sh//2-r):sh//2+r,
                                      max(0,int(s*sec_w+15)-r):int(s*sec_w+15)+r]))
              for s in range(6)]
        return LEVEL_OPTIONS[int(np.argmax(px))]
    except Exception:
        return "Intermediate"


def get_fixed_vertical_bounds(image):
    h = image.shape[0]
    return int(h * 0.22), int(h * 0.59)


def detect_name_x_anchor(image):
    try:
        h, w = image.shape[:2]
        roi  = image[int(h * 0.23):int(h * 0.52), int(w * 0.05):int(w * 0.75)]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        th   = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY_INV, 15, 3)
        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        xs = []
        for c in contours:
            x, y, w_box, h_box = cv2.boundingRect(c)
            if 50 < cv2.contourArea(c) < 600 and 8 < w_box < 25:
                xs.append(x + w_box // 2)
        if len(xs) < 50:
            return None
        return int(np.mean(xs))
    except Exception:
        return None


def extract_name_region(image):
    try:
        h, w = image.shape[:2]
        y1, y2 = get_fixed_vertical_bounds(image)
        cx = detect_name_x_anchor(image)
        if cx is None:
            return image[y1:y2, int(w * 0.08):int(w * 0.72)]
        box_w = int(w * 0.72)
        x1 = max(0, cx - box_w // 2)
        x2 = min(w, cx + box_w // 2)
        return image[y1:y2, x1:x2]
    except Exception:
        h, w = image.shape[:2]
        return image[int(h*0.22):int(h*0.59), int(w*0.08):int(w*0.72)]


def extract_name(name_img):
    try:
        gray = cv2.cvtColor(name_img, cv2.COLOR_BGR2GRAY)

        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bubbles = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            if 40 < area < 1000 and 6 < w < 35 and 6 < h < 35:
                bubbles.append((x, y, w, h, c))

        if len(bubbles) < 100:
            return ""

        bubbles = sorted(bubbles, key=lambda b: b[1])
        rows, current, last_y = [], [], None
        for b in bubbles:
            x, y, w, h, c = b
            if last_y is None:
                last_y = y
            if abs(y - last_y) < 18:
                current.append(b)
            else:
                rows.append(current)
                current = [b]
                last_y = y
        if current:
            rows.append(current)
        rows = sorted(rows, key=lambda r: len(r), reverse=True)[:26]
        rows = sorted(rows, key=lambda r: np.mean([b[1] for b in r]))

        if not rows:
            return ""

        all_x = sorted([b[0] for r in rows for b in r])
        col_positions = []
        for x in all_x:
            if not col_positions or abs(x - col_positions[-1]) > 12:
                col_positions.append(x)

        if not col_positions:
            return ""

        grid = [[None]*len(col_positions) for _ in range(len(rows))]
        for r_idx, row in enumerate(rows):
            for b in row:
                x, y, w, h, c = b
                dists = [abs(x - cx) for cx in col_positions]
                idx = int(np.argmin(dists))
                grid[r_idx][idx] = b

        all_col_data = []
        col_max_values = []
        col_max_ratios = []

        for col in range(len(col_positions)):
            values, ratios = [], []
            for row in range(len(rows)):
                b = grid[row][col]
                if b is None:
                    values.append(0)
                    ratios.append(0.0)
                    continue
                x, y, w, h, c = b
                mask = np.zeros(thresh.shape, dtype="uint8")
                cv2.drawContours(mask, [c], -1, 255, -1)
                filled = cv2.countNonZero(cv2.bitwise_and(thresh, thresh, mask=mask))
                bubble_area = cv2.countNonZero(mask)
                ratio = filled / bubble_area if bubble_area > 0 else 0.0
                values.append(filled)
                ratios.append(ratio)

            max_val = max(values) if values else 0
            max_ratio = max(ratios) if ratios else 0.0
            sorted_vals = sorted(values, reverse=True)
            second = sorted_vals[1] if len(sorted_vals) > 1 else 0
            sorted_ratios = sorted(ratios, reverse=True)
            second_ratio = sorted_ratios[1] if len(sorted_ratios) > 1 else 0.0

            col_max_values.append(max_val)
            col_max_ratios.append(max_ratio)
            all_col_data.append((values, ratios, max_val, second, max_ratio, second_ratio))

        if not col_max_values:
            return ""

        avg_max = np.mean(col_max_values)
        threshold = avg_max * 0.65

        MIN_RATIO = 0.45
        STRONG_DIFF = 15
        MIN_RATIO_DIFF = 0.10

        def col_is_valid(col_idx):
            if col_idx < 0 or col_idx >= len(all_col_data):
                return False
            vals, ratios, mx, sec, max_ratio, second_ratio = all_col_data[col_idx]
            d          = mx - sec
            ratio_diff = max_ratio - second_ratio
            passes_ratio = max_ratio >= MIN_RATIO and ratio_diff >= MIN_RATIO_DIFF
            passes_diff = d >= STRONG_DIFF and mx >= threshold
            return (passes_diff and passes_ratio) or d >= 80

        name, col = "", 0
        while col < len(all_col_data):
            values, ratios, max_val, second, max_ratio, second_ratio = all_col_data[col]
            diff       = max_val - second
            ratio_diff = max_ratio - second_ratio
            is_valid   = col_is_valid(col)

            if not is_valid:
                is_space = (
                    len(name) >= 4
                    and diff < 10
                    and col_is_valid(col - 1)
                    and col_is_valid(col + 1)
                )
                if is_space:
                    if name[-1] != " ":
                        name += " "
                    col += 1
                    continue
                next_valid = col_is_valid(col + 1)
                if not next_valid:
                    break
                else:
                    if len(name) >= 1 and name[-1] != " ":
                        name += " "
                    col += 1
                    continue

            row_idx = values.index(max_val)
            if row_idx < len(LETTERS):
                name += LETTERS[row_idx]
            col += 1

        return name.strip()
    except Exception:
        return ""


def extract_centre_number(image):
    try:
        h, w = image.shape[:2]
        area = image[int(0.24*h):int(0.40*h), int(0.72*w):int(0.92*w)]
        gray = cv2.cvtColor(area, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5,5), 0)
        ah, aw = area.shape[:2]

        cs = _detect_circles(gray)
        col_c = sorted(_cluster_centers([int(c[0]) for c in cs], gap=15))[:5] if cs is not None else []
        row_c = sorted(_cluster_centers([int(c[1]) for c in cs], gap=15))[:10] if cs is not None else []
        if len(col_c) < 5: col_c = [int((i+0.5)*aw/5) for i in range(5)]
        if len(row_c) < 10: row_c = [int((i+0.5)*ah/10) for i in range(10)]

        result = []
        for cx in col_c:
            scores = []
            for ry in row_c:
                candidates = [c for c in cs if abs(int(c[1])-ry) <= 12] if cs is not None else []
                if candidates:
                    bc, dist2 = _closest_xy(candidates, cx, ry)
                else:
                    bc, dist2 = None, float("inf")
                if bc is not None and dist2 < 16*16:
                    d = _bubble_darkness(gray, int(bc[0]), int(bc[1]), int(bc[2]))
                else:
                    d = _bubble_darkness_at(gray, cx, ry, r=10)
                scores.append(d)

            if not scores:
                result.append("_")
                continue

            arr  = np.array(sorted(scores))
            gaps = [(arr[i+1]-arr[i], (arr[i]+arr[i+1])/2) for i in range(len(arr)-1)]
            if not gaps:
                result.append("_")
                continue
            best_gap, thr = max(gaps, key=lambda x: x[0])
            if best_gap < 8:
                result.append("_")
                continue
            filled = [i for i, s in enumerate(scores) if s >= thr]
            result.append(DIGITS[filled[0]] if len(filled) == 1 else "_")
        return "".join(result)
    except Exception:
        return "_____"


def extract_dob(image):
    try:
        h, w = image.shape[:2]
        area = image[int(0.448*h):int(0.624*h), int(0.698*w):int(0.998*w)]
        gray = cv2.cvtColor(area, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5,5), 0)
        dh, dw = area.shape[:2]

        cs = _detect_circles(gray)
        col_c = sorted(_cluster_centers([int(c[0]) for c in cs], gap=15))[:8] if cs is not None else []
        row_c = sorted(_cluster_centers([int(c[1]) for c in cs], gap=15))[:10] if cs is not None else []
        if len(col_c) < 8: col_c = [int((i+0.5)*dw/8) for i in range(8)]
        if len(row_c) < 10: row_c = [int((i+0.5)*dh/10) for i in range(10)]

        radii = [int(c[2]) for c in cs] if cs is not None and len(cs) > 0 else []
        med_r = int(np.median(radii)) if radii else 10

        result = []
        for cx in col_c:
            scores = []
            for ry in row_c:
                candidates = [c for c in cs if abs(int(c[1])-ry) <= 12] if cs is not None else []
                if candidates:
                    bc, dist2 = _closest_xy(candidates, cx, ry)
                else:
                    bc, dist2 = None, float("inf")
                if bc is not None and dist2 <= DOB_MAX_GRID_DIST**2:
                    d = _bubble_darkness(gray, int(bc[0]), int(bc[1]), int(bc[2]))
                else:
                    d = _bubble_darkness_at(gray, cx, ry, r=int(med_r*1.2))
                scores.append(d)

            if not scores:
                result.append("_")
                continue

            arr  = np.array(sorted(scores))
            gaps = [(arr[i+1]-arr[i], (arr[i]+arr[i+1])/2) for i in range(len(arr)-1)]
            if not gaps:
                result.append("_")
                continue
            best_gap, thr = max(gaps, key=lambda x: x[0])
            if best_gap <= 8:
                result.append("_")
                continue
            scores_np = np.array(scores)
            score_range = scores_np.max() - scores_np.min()
            scores_np = (scores_np - scores_np.min()) / (score_range + 1e-6)
            top2 = sorted(scores_np, reverse=True)
            if len(top2) < 2 or top2[0] - top2[1] < 0.15:
                result.append("_")
                continue
            result.append(DIGITS[int(np.argmax(scores_np))])

        raw = "".join(result)
        return f"{raw[0:2]}/{raw[2:4]}/{raw[4:8]}" if len(raw) == 8 else raw
    except Exception:
        return ""


def extract_answers(image):
    try:
        h, w = image.shape[:2]
        area = image[int(0.643*h):int(0.885*h), int(0.02*w):int(0.98*w)]
        aw = area.shape[1]
        gw = aw // NUM_ANSWER_GROUPS

        all_scores, group_cache = [], []

        for g in range(NUM_ANSWER_GROUPS):
            grp = area[:, g*gw:(g+1)*gw]
            gray = cv2.cvtColor(grp, cv2.COLOR_BGR2GRAY)
            cs = _detect_circles(gray)
            MAX_BUBBLE_R = 15
            cs_for_rows = np.array([c for c in cs if c[2] <= MAX_BUBBLE_R]) if cs is not None else None

            raw_col_vals = [int(c[0]) for c in cs_for_rows]
            raw_row_vals = [int(c[1]) for c in cs_for_rows]
            col_clusters = _cluster_centers(raw_col_vals)
            row_clusters = _cluster_centers(raw_row_vals)

            col_c = sorted(col_clusters)[-OPTIONS_PER_QUESTION:] if col_clusters else []
            valid_row_clusters = [ry for ry in row_clusters
                      if len([c for c in cs if abs(int(c[1])-ry) <= CLUSTER_GAP]) >= 3]
            row_c = sorted(valid_row_clusters)[:ROWS_PER_GROUP] if valid_row_clusters else sorted(row_clusters)[:ROWS_PER_GROUP]

            if not col_c or not row_c:
                group_cache.append(None)
                continue

            rows = []
            for ri, ry in enumerate(row_c):
                row_cs = [c for c in cs if abs(int(c[1])-ry) <= CLUSTER_GAP]
                scores, bcs = [], []
                for cx in col_c:
                    bc = _closest_x(row_cs, cx) if row_cs else None
                    d  = _bubble_darkness(gray, int(bc[0]), int(bc[1]), int(bc[2])) if bc is not None else 0.0
                    scores.append(d)
                    bcs.append(bc)
                    all_scores.append(d)
                rows.append((ri, ry, scores, bcs))
            group_cache.append((g, gray, col_c, rows))

        threshold = _find_adaptive_threshold(all_scores)
        results   = {}

        for item in group_cache:
            if item is None:
                continue
            g, gray, col_c, rows = item
            for ri, ry, scores, bcs in rows:
                q = g * ROWS_PER_GROUP + ri + 1
                if not scores:
                    results[str(q)] = "-"
                    continue

                status, answer = _classify_bubble(scores, threshold)

                if status == "EMPTY" and max(scores) > 0:
                    arr = np.array(scores)
                    best_idx = int(np.argmax(arr))
                    sorted_s = sorted(arr, reverse=True)
                    if sorted_s[0] >= 60 and (len(sorted_s) < 2 or sorted_s[1] == 0 or sorted_s[0] / (sorted_s[1] + 1e-9) >= 1.5):
                        status = "OK"
                        answer = OPTIONS[best_idx]

                if status == "MULTIPLE":
                    results[str(q)] = "&".join(answer)
                elif status == "OK":
                    results[str(q)] = answer
                else:
                    results[str(q)] = "-"

        return results
    except Exception as e:
        print(f"extract_answers error: {e}")
        return {str(q): "-" for q in range(1, 41)}

def process_sheet(path):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot read '{path}'")

    img = auto_straighten(auto_straighten(img))

    name_region = extract_name_region(img)

    result = {
        "name": extract_name(name_region),
        "level": detect_level(img),
        "centre_number": extract_centre_number(img),
        "dob": extract_dob(img),
        "answers": extract_answers(img),
    }

    return result


def process_omr_file(file_path):
    try:
        result = process_sheet(file_path)

        formatted_answers = {}

        for q in range(1, 41):
            val = result["answers"].get(str(q))

            if val is None or val == "":
                formatted_answers[str(q)] = ""
            elif val == "-":
                formatted_answers[str(q)] = "-"
            elif "&" in str(val):
                formatted_answers[str(q)] = val
            else:
                formatted_answers[str(q)] = val

        return {
            "name": result["name"],
            "centre_number": result["centre_number"],
            "dob": result["dob"],
            "level": result["level"],
            "answers": formatted_answers
        }

    except FileNotFoundError as e:
        return {"error": str(e)}
    except Exception as e:
        print(f"process_omr_file error [{file_path}]: {e}")
        return {"error": str(e)}