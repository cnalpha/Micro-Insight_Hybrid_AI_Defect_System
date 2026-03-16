import cv2
import numpy as np
import os
import math
import pandas as pd
from ultralytics import YOLO

# ==========================================================================================
# [V13.16 系統說明]
# 版本名稱：Polarity Control Edition (極性控制版) - 雜質修復版 + CSV報表/純數字ID標註 + FDC整合
# ==========================================================================================

class SemiGuardianInspectorV13_16:
    def __init__(self, model_path, 
                 pixel_to_um=0.5,
                 default_conf=0.25,
                 save_result=True,
                 defect_polarity='BRIGHT', 
                 link_gap_dist=20,      
                 link_gap_angle=20,     
                 patch_merge=15,            
                 patch_small_thresh=30,     
                 patch_shrink_max=7,        
                 patch_shrink_min=1,        
                 inclusion_fusion_assist=3, 
                 inclusion_global_merge=5): 
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"找不到模型檔案: {model_path}")
            
        print(f"[V13.16 系統] 初始化... (極性控制版 | 極性設定: {defect_polarity})")
        print(f"   - Scratches: Polarity Control ({defect_polarity}) + Post-Connect")
        print(f"   - Inclusion: Forced DARK Polarity (反向二值化)")
        
        self.model = YOLO(model_path)
        
        class DynamicConfig: pass
        self.config = DynamicConfig()
        
        self.config.PIXEL_TO_UM = pixel_to_um
        self.config.DEFAULT_CONF = default_conf
        self.config.SAVE_RESULT = save_result
        self.config.DEFECT_POLARITY = defect_polarity.upper()
        
        self.config.LINK_GAP_DIST = link_gap_dist
        self.config.LINK_GAP_ANGLE = link_gap_angle
        self.config.PATCH_MERGE = patch_merge
        self.config.PATCH_SMALL_THRESH = patch_small_thresh
        self.config.PATCH_SHRINK_MAX = patch_shrink_max
        self.config.PATCH_SHRINK_MIN = patch_shrink_min
        self.config.INCLUSION_FUSION_ASSIST = inclusion_fusion_assist
        self.config.INCLUSION_GLOBAL_MERGE = inclusion_global_merge
        
        self._init_kernels()

    def _init_kernels(self):
        c = self.config
        self.k_patch = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (c.PATCH_MERGE, c.PATCH_MERGE)) if c.PATCH_MERGE > 0 else None
        self.k_inc_assist = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (c.INCLUSION_FUSION_ASSIST, c.INCLUSION_FUSION_ASSIST)) if c.INCLUSION_FUSION_ASSIST > 0 else None
        self.k_inc_merge = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (c.INCLUSION_GLOBAL_MERGE, c.INCLUSION_GLOBAL_MERGE)) if c.INCLUSION_GLOBAL_MERGE > 0 else None

    def _post_process_connect(self, mask):
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if len(cnts) < 2: return mask 
        
        segments = []
        for i, cnt in enumerate(cnts):
            if cv2.contourArea(cnt) < 10: continue
            rect = cv2.minAreaRect(cnt)
            (cx, cy), (w, h), angle = rect
            if w < h: angle += 90 
            segments.append({'id': i, 'center': (cx, cy), 'angle': angle, 'cnt': cnt})
            
        canvas = mask.copy()
        for i in range(len(segments)):
            for j in range(i + 1, len(segments)):
                s1 = segments[i]
                s2 = segments[j]
                
                dist = math.sqrt((s1['center'][0]-s2['center'][0])**2 + (s1['center'][1]-s2['center'][1])**2)
                angle_diff = abs(s1['angle'] - s2['angle'])
                if angle_diff > 90: angle_diff = 180 - angle_diff
                
                link_angle = math.degrees(math.atan2(s2['center'][1]-s1['center'][1], s2['center'][0]-s1['center'][0]))
                link_diff = abs(s1['angle'] - link_angle)
                if link_diff > 90: link_diff = 180 - link_diff
                
                if angle_diff < self.config.LINK_GAP_ANGLE and link_diff < self.config.LINK_GAP_ANGLE:
                    if dist < self.config.LINK_GAP_DIST * 3: 
                         cv2.line(canvas, (int(s1['center'][0]), int(s1['center'][1])), 
                                  (int(s2['center'][0]), int(s2['center'][1])), (255), 2)
        return canvas

    def inspect(self, image_path, output_dir):
        c = self.config
        if not os.path.exists(image_path): return []
        
        print(f"[V13.16 執行] 分析中: {os.path.basename(image_path)}")
        results = self.model.predict(image_path, conf=c.DEFAULT_CONF, verbose=False)[0]
        original_img = results.orig_img.copy()
        h, w = original_img.shape[:2]
        
        global_mask = np.zeros((h, w), dtype=np.uint8)
        annotated_img = np.zeros((h, w, 3), dtype=np.uint8) 
        output_results = []
        defect_id = 0

        unique_classes = np.unique(results.boxes.cls.cpu().numpy())
        boxes = results.boxes.xyxy.cpu().numpy()
        classes = results.boxes.cls.cpu().numpy()

        for cls_id in unique_classes:
            name = self.model.names[int(cls_id)]
            idxs = np.where(classes == cls_id)[0]
            class_mask = np.zeros((h, w), dtype=np.uint8)
            
            # === 1. Scratches ===
            if name == 'scratches':
                for idx in idxs:
                    x1, y1, x2, y2 = map(int, boxes[idx])
                    x1, y1 = max(0, x1), max(0, y1); x2, y2 = min(w, x2), min(h, y2)
                    roi_bgr = original_img[y1:y2, x1:x2]
                    if roi_bgr.size == 0: continue
                    roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
                    roi_blurred = cv2.GaussianBlur(roi_gray, (3, 3), 0)
                    
                    if c.DEFECT_POLARITY == 'BRIGHT':
                        _, binary_roi = cv2.threshold(roi_blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    else:
                        _, binary_roi = cv2.threshold(roi_blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                        
                    class_mask[y1:y2, x1:x2] = cv2.bitwise_or(class_mask[y1:y2, x1:x2], binary_roi)
                
                class_mask = self._post_process_connect(class_mask)

            # === 2. Patches ===
            elif name == 'patches':
                for idx in idxs:
                    x1, y1, x2, y2 = map(int, boxes[idx])
                    box_w, box_h = x2 - x1, y2 - y1
                    min_side = min(box_w, box_h)
                    s = c.PATCH_SHRINK_MIN if min_side < c.PATCH_SMALL_THRESH else c.PATCH_SHRINK_MAX 
                    sx1, sy1 = max(x1, x1 + s), max(y1, y1 + s)
                    sx2, sy2 = min(x2, x2 - s), min(y2, y2 - s)
                    if sx2 <= sx1: cx = (x1 + x2) // 2; sx1, sx2 = cx, cx + 1
                    if sy2 <= sy1: cy = (y1 + y2) // 2; sy1, sy2 = cy, cy + 1
                    cv2.rectangle(class_mask, (sx1, sy1), (sx2, sy2), 255, -1)
                
                if self.k_patch is not None:
                    class_mask = cv2.morphologyEx(class_mask, cv2.MORPH_CLOSE, self.k_patch)

            # === 3. Inclusion ===
            elif name == 'inclusion':
                for idx in idxs:
                    x1, y1, x2, y2 = map(int, boxes[idx])
                    x1, y1 = max(0, x1), max(0, y1); x2, y2 = min(w, x2), min(h, y2)
                    roi_bgr = original_img[y1:y2, x1:x2]
                    if roi_bgr.size == 0: continue
                    roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
                    roi_blurred = cv2.GaussianBlur(roi_gray, (5, 5), 0)
                    
                    _, binary_roi = cv2.threshold(roi_blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                    if self.k_inc_assist is not None:
                        binary_roi = cv2.dilate(binary_roi, self.k_inc_assist, iterations=1)
                    class_mask[y1:y2, x1:x2] = cv2.bitwise_or(class_mask[y1:y2, x1:x2], binary_roi)
                
                if self.k_inc_merge is not None:
                    class_mask = cv2.morphologyEx(class_mask, cv2.MORPH_CLOSE, self.k_inc_merge)

            # --- 融合與測量 ---
            global_mask = cv2.bitwise_or(global_mask, class_mask)
            cnts, _ = cv2.findContours(class_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = sorted(cnts, key=lambda c: cv2.boundingRect(c)[1])
            
            for cnt in cnts:
                if cv2.contourArea(cnt) < 5: continue
                self._draw_and_measure(annotated_img, cnt, name, defect_id, output_results)
                defect_id += 1

        if c.SAVE_RESULT:
            if not os.path.exists(output_dir): os.makedirs(output_dir)
            mask_name = f"result_V13_16_PixelMask_{os.path.basename(image_path)}"
            cv2.imwrite(os.path.join(output_dir, mask_name), global_mask)
            out_name = f"result_V13_16_Annotated_{os.path.basename(image_path)}"
            cv2.imwrite(os.path.join(output_dir, out_name), annotated_img)
            print(f"[成功] 像素圖: {mask_name}")
            
        return output_results

    def _draw_and_measure(self, img, cnt, cls_name, did, results_list):
        metrics = {}
        area_px = cv2.contourArea(cnt)
        metrics['area_um2'] = area_px * (self.config.PIXEL_TO_UM ** 2)
        
        rect = cv2.minAreaRect(cnt)
        (c), (w, h), a = rect
        span_len_um = max(w, h) * self.config.PIXEL_TO_UM
        
        display_val = 0
        if cls_name == 'scratches':
            perimeter = cv2.arcLength(cnt, True)
            curve_len_um = (perimeter / 2) * self.config.PIXEL_TO_UM
            display_val = max(span_len_um, curve_len_um)
            metrics['display_unit'] = 'um (Len)'
        elif cls_name == 'patches':
            display_val = metrics['area_um2']
            metrics['display_unit'] = 'um^2 (Area)'
        else:
            (x, y), radius = cv2.minEnclosingCircle(cnt)
            display_val = (radius * 2) * self.config.PIXEL_TO_UM
            metrics['display_unit'] = 'um (Dia)'

        metrics['span_length_um'] = span_len_um
        metrics['display_value'] = display_val

        cv2.drawContours(img, [cnt], -1, (255, 255, 255), -1) 
        x, y, w, h = cv2.boundingRect(cnt)
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 0, 255), 1)
        
        metrics['center_x_px'] = x + w // 2
        metrics['center_y_px'] = y + h // 2
        metrics['box_w_px'] = w
        metrics['box_h_px'] = h

        label = str(did)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.3  
        thickness = 1     
        
        text_y = y - 5 if y - 5 > 10 else y + 15
        cv2.putText(img, label, (x, text_y), font, font_scale, (0, 255, 0), thickness)
        
        results_list.append({'id': did, 'class': cls_name, 'metrics': metrics})

# ==========================================================
# [新增] Module C: FDC 智慧製程回饋系統
# ==========================================================
class FDC_System:
    def __init__(self, size_threshold=50.0, alarm_streak=3, loc_tolerance=20.0):
        self.size_threshold = size_threshold      
        self.alarm_streak = alarm_streak          
        self.loc_tolerance = loc_tolerance        
        self.history_locations = []               

    def calculate_distance(self, p1, p2):
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

    def is_same_location(self, current_loc):
        # 如果歷史記錄的數量不夠 (例如要連續3片，歷史至少要有前2片)
        if len(self.history_locations) < self.alarm_streak - 1:
            return False 

        streak_count = 1 # 當前這片晶圓算第 1 次
        
        # 從最近的歷史記錄往前推
        for past_wafer_defects in reversed(self.history_locations):
            match_found = False
            for past_loc in past_wafer_defects:
                if self.calculate_distance(current_loc, past_loc) <= self.loc_tolerance:
                    match_found = True
                    break
            
            if match_found:
                streak_count += 1
            else:
                break # 只要前一片沒有，連續性就中斷了
                
        return streak_count >= self.alarm_streak

    def decide_action(self, current_defects):
        current_locs = [(d['x'], d['y']) for d in current_defects]

        # ==========================================================
        # 規則 1 修正：收集所有致命瑕疵 (STOP)
        # ==========================================================
        oversized_defects = []
        for defect in current_defects:
            if defect['length'] > self.size_threshold:
                oversized_defects.append(f"ID:{defect['id']} ({defect['length']:.2f}um)")

        if oversized_defects:
            defect_details = ", ".join(oversized_defects)
            # 發生 STOP 時，也要將記錄寫入歷史，以免後續數據斷層
            self.history_locations.append(current_locs)
            if len(self.history_locations) > self.alarm_streak:
                self.history_locations.pop(0)
            return "STOP", f"🚨 偵測到 {len(oversized_defects)} 個瑕疵超過停機標準！名單: {defect_details}"

        # ==========================================================
        # 規則 2: 系統性污染警報 (ALARM)
        # ==========================================================
        action = "PASS"
        message = "機台狀況正常，繼續生產。"

        for loc in current_locs:
            if self.is_same_location(loc):
                action = "ALARM"
                message = f"連續 {self.alarm_streak} 片晶圓在座標 {loc} 附近出現瑕疵，疑似機台污染！"
                
                # ==========================================================
                # [關鍵修復] 觸發警報後，清空歷史記憶 (模擬機台已被工程師清潔保養)
                # ==========================================================
                self.history_locations.clear()
                return action, message # 直接回傳，不再把當前資料寫入歷史

        # ==========================================================
        # 沒觸發警報，才把這片晶圓的座標寫入歷史記憶
        # ==========================================================
        self.history_locations.append(current_locs)
        
        if len(self.history_locations) > self.alarm_streak:
            self.history_locations.pop(0)

        return action, message


# ==========================================================
# 主程式執行區塊 (全資料夾批次掃描 + 終端機總結報表)
# ==========================================================
if __name__ == "__main__":
    MODEL = r"C:\Users\user\CnLearning\AIChatGPT\Module_B_Vision\OpenCV\best.pt"
    # ⚠️ 指定你的圖片資料夾與輸出資料夾
    INPUT_DIR = r"C:\Users\user\CnLearning\AIChatGPT\Module_B_Vision\OpenCV\images" 
    OUTPUT_DIR = r"C:\Users\user\CnLearning\AIChatGPT\Module_B_Vision\OpenCV\results"
    
    if os.path.exists(MODEL) and os.path.exists(INPUT_DIR):
        # 1. 初始化系統
        inspector = SemiGuardianInspectorV13_16(
            MODEL, default_conf=0.25, defect_polarity='BRIGHT', 
            link_gap_dist=10, link_gap_angle=5, patch_merge=15,
            patch_shrink_max=7, patch_shrink_min=1, inclusion_fusion_assist=3, inclusion_global_merge=5
        )
        
        # [測試 ALARM 專用設定] 將 size_threshold 調到極大 (9999.0)，避免被 STOP 攔截
        # 測試完畢後，記得改回 50.0 恢復正常產線邏輯
        fdc = FDC_System(size_threshold=50, alarm_streak=3, loc_tolerance=20.0)
        
        # 2. 抓取資料夾內所有圖片並排序
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
        image_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(valid_extensions)]
        image_files.sort() 
        
        if not image_files:
            print(f"在資料夾 {INPUT_DIR} 中找不到任何圖片！")
        else:
            print(f"\n🚀 [系統啟動] 找到 {len(image_files)} 張圖片，開始進行產線自動化批次掃描...\n")
            
            # 準備一個大清單，用來收集所有圖片的最終結果
            final_summary_report = []
            all_report_data_for_csv = []
            
            # 3. 迴圈依序處理每一張圖
            for wafer_count, img_name in enumerate(image_files, start=1):
                current_img_path = os.path.join(INPUT_DIR, img_name)
                
                # 執行視覺檢測
                results = inspector.inspect(current_img_path, OUTPUT_DIR)
                
                current_defects_for_fdc = [] 
                defect_log_strings = [] # 用來記錄這張圖的所有瑕疵字串
                
                for r in results:
                    m = r['metrics']
                    cls = r['class']
                    val_str = f"{m['display_value']:>6.2f} {m['display_unit']}"
                    
                    # 收集 CSV 報表資料
                    all_report_data_for_csv.append({
                        'Wafer_Image': img_name,
                        'Defect_ID': r['id'],
                        'Class': cls,
                        'Measurement': val_str,
                        'Area (um^2)': round(m['area_um2'], 2),
                        'Center_X (px)': m['center_x_px'],
                        'Center_Y (px)': m['center_y_px']
                    })
                    
                    # 收集 FDC 所需資料
                    current_defects_for_fdc.append({
                        'id': r['id'],
                        'length': m['display_value'], 
                        'x': m['center_x_px'],
                        'y': m['center_y_px']
                    })
                    
                    defect_log_strings.append(f"ID:{r['id']}({val_str})")
                
                # 觸發 Module C 邏輯判斷
                action, fdc_message = fdc.decide_action(current_defects_for_fdc)
                
                # 將這片晶圓的綜合結果存入總結報表
                final_summary_report.append({
                    'wafer_num': wafer_count,
                    'image_name': img_name,
                    'defect_count': len(results),
                    'defect_list': ", ".join(defect_log_strings) if defect_log_strings else "無瑕疵",
                    'action': action,
                    'message': fdc_message
                })

            # ==========================================================
            # 4. 終端機：印出最終總結報表給工程師看
            # ==========================================================
            print("\n" + "="*80)
            print("                📊 Semi-Guardian Pro 產線批次檢測總結報告")
            print("="*80)
            print(f"總檢測晶圓數: {len(image_files)} 片")
            print("-" * 80)
            
            for report in final_summary_report:
                print(f"▶ [Wafer {report['wafer_num']:02d}] 檔案: {report['image_name']}")
                print(f"   - 視覺檢測: 共發現 {report['defect_count']} 個瑕疵 => {report['defect_list']}")
                
                if report['action'] == "STOP":
                    print(f"   - FDC 判定: 🚨 {report['action']} -> {report['message']}")
                elif report['action'] == "ALARM":
                    print(f"   - FDC 判定: ⚠️ {report['action']} -> {report['message']}")
                else:
                    print(f"   - FDC 判定: ✅ {report['action']} -> {report['message']}")
                print("-" * 80)
            
            print("="*80 + "\n")

            # 匯出包含所有圖片數據的總 CSV 報表
            if all_report_data_for_csv:
                df = pd.DataFrame(all_report_data_for_csv)
                csv_path = os.path.join(OUTPUT_DIR, "Batch_Defect_Report_All.csv")
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                print(f"💾 [系統提示] 包含所有晶圓細節的 CSV 總表已匯出至: {csv_path}\n")

    else:
        print("請確認 MODEL 與 INPUT_DIR 的路徑是否正確！")