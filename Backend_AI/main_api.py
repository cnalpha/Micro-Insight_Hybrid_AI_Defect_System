from fastapi import FastAPI, File, UploadFile
import uvicorn
import os
import shutil

# 1. 載入你剛剛寫好的核心引擎 (請確保你的檔案已經改名為 my_inspector.py 或維持 main.py，需與你的檔名一致)
from main import SemiGuardianInspectorV13_16, FDC_System

# 2. 建立 FastAPI 應用程式實體
app = FastAPI(
    title="Semi-Guardian Pro API", 
    description="全域半導體智慧檢測與 FDC 回饋系統 API",
    version="13.16"
)

# =====================================================================
# 系統初始化區塊 (伺服器啟動時只載入一次模型，這對產線的檢測速度至關重要)
# =====================================================================
# [修改重點] 自動取得目前 main_api.py 所在的資料夾路徑 (即 Backend_AI 資料夾)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 使用 os.path.join 動態組合相對路徑
MODEL_PATH = os.path.join(BASE_DIR, "best.pt")
TEMP_DIR = os.path.join(BASE_DIR, "api_temp")

# 建立暫存資料夾用來存放機台透過網路傳來的圖片
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

print("\n🚀 [API 伺服器啟動中] 正在載入 AI 模型與 FDC 規則...")

# 初始化 Module B (視覺檢測)
inspector = SemiGuardianInspectorV13_16(
    MODEL_PATH, default_conf=0.25, defect_polarity='BRIGHT', 
    link_gap_dist=10, link_gap_angle=5, patch_merge=15,
    patch_shrink_max=7, patch_shrink_min=1, inclusion_fusion_assist=3, inclusion_global_merge=5
)

# 初始化 Module C (設定停機標準 50um，與你主程式的實戰規格一致)
fdc = FDC_System(size_threshold=50.0, alarm_streak=3, loc_tolerance=20.0)

print("✅ [系統就緒] 伺服器已啟動，等待產線機台連線與呼叫...\n")


# =====================================================================
# API 路由 (Endpoint)：機台專用的檢測接口
# =====================================================================
@app.post("/inspect_wafer/")
async def inspect_wafer(file: UploadFile = File(...)):
    """
    接收機台傳來的晶圓圖片，進行 AI 檢測與 FDC 判斷，回傳 JSON 結果。
    """
    try:
        # 1. 接收機台上傳的圖片，並暫存到伺服器的資料夾中
        temp_img_path = os.path.join(TEMP_DIR, file.filename)
        with open(temp_img_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. 呼叫 Module B 進行視覺檢測
        results = inspector.inspect(temp_img_path, TEMP_DIR)

        # 整理 FDC 與 JSON 報表需要的數據格式
        current_defects_for_fdc = []
        defect_details = []
        raw_defects = [] # 🌟 [新增] 用來儲存給 CSV 的原始數據
        
        for r in results:
            m = r['metrics']
            cls = r['class'] # 🌟 [新增] 抓取瑕疵種類
            
            current_defects_for_fdc.append({
                'id': r['id'],
                'length': m['display_value'],
                'x': m['center_x_px'],
                'y': m['center_y_px']
            })
            val_str = f"{m['display_value']:.2f} {m['display_unit']}"
            defect_details.append(f"ID:{r['id']} ({val_str})")
            
            # 🌟 [新增] 將詳細數據打包成字典，準備傳給 C#
            raw_defects.append({
                'Defect_ID': r['id'],
                'Class': cls,
                'Measurement': val_str,
                'Area_um2': round(m['area_um2'], 2),
                'Center_X': m['center_x_px'],
                'Center_Y': m['center_y_px']
            })

        # 3. 呼叫 Module C 進行 FDC 邏輯判斷
        action, fdc_message = fdc.decide_action(current_defects_for_fdc)

        # 4. 將所有結果打包成乾淨的 JSON 格式回傳給機台
        # 這就是前後端分離的精髓，前端 C# 只需要解析這個 JSON 就能亮紅綠燈
        return {
            "status": "success",
            "filename": file.filename,
            "defect_count": len(results),
            "defects_list": defect_details,
            "raw_defects": raw_defects,  # 🌟 [新增] 把這包原始資料傳給 C#
            "fdc_action": action,        # 關鍵指令: PASS, STOP, 或 ALARM
            "fdc_message": fdc_message   # 系統說明的字串
        }

    except Exception as e:
        # 如果發生錯誤，優雅地回傳錯誤訊息，避免機台當機
        return {"status": "error", "message": str(e)}

# =====================================================================
# 啟動指令碼
# =====================================================================
if __name__ == "__main__":
    # 使用 uvicorn 在本機 (127.0.0.1) 的 8000 port 啟動 API 服務
    uvicorn.run(app, host="127.0.0.1", port=8000)