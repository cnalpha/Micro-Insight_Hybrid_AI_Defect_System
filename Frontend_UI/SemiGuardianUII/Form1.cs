using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using System.Windows.Forms;
using Newtonsoft.Json.Linq;

namespace SemiGuardianUII
{
    public partial class Form1 : Form
    {
        // =========================================================
        // 系統連線與路徑設定
        // =========================================================
        private readonly string apiUrl = "http://127.0.0.1:8000/inspect_wafer/";

        // 🚨 維持你原本的絕對路徑設定
        private readonly string tempDir = @"C:\Users\user\CnLearning\Micro-Insight_Hybrid_AI_Defect_System\Backend_AI\api_temp";

        // 🌟 [新增] 用來收集 CSV 報表資料的清單
        private List<string> csvDataLines = new List<string>();

        // UI 元件
        private ListBox lstDefects;
        private Button btnPrev;
        private Button btnNext;
        private Button btnPauseResume; // 暫停/繼續按鈕

        // 🌟 [新增] 開啟 CSV 按鈕與路徑記錄
        private Button btnOpenCsv;
        private string latestCsvPath = "";

        // =========================================================
        // 歷史記憶庫結構與暫停狀態開關
        // =========================================================
        public class WaferRecord
        {
            public string FileName { get; set; }
            public string AnnotatedImagePath { get; set; }
            public string ActionText { get; set; }
            public Color ActionColor { get; set; }
            public string Message { get; set; }
        }

        private List<WaferRecord> reviewHistory = new List<WaferRecord>();
        private int currentReviewIndex = -1;

        // 控制系統是否暫停的全域變數
        private bool isPaused = false;

        public Form1()
        {
            InitializeComponent();
            SetupModernUI();
        }

        private void SetupModernUI()
        {
            this.Text = "Micro-Insight: Hybrid AI Defect Profiling System";
            this.Size = new Size(1350, 800);
            this.BackColor = Color.FromArgb(30, 30, 30);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.MinimumSize = new Size(1100, 600);

            // 1. 頂部面板
            Panel headerPanel = new Panel();
            headerPanel.Height = 130;
            headerPanel.Dock = DockStyle.Top;
            headerPanel.BackColor = Color.FromArgb(45, 45, 48);
            this.Controls.Add(headerPanel);

            // 載入按鈕
            btnInspect.Text = "📂 批次檢測";
            btnInspect.Size = new Size(180, 50);
            btnInspect.Location = new Point(20, 40);
            btnInspect.Font = new Font("微軟正黑體", 14, FontStyle.Bold);
            btnInspect.FlatStyle = FlatStyle.Flat;
            btnInspect.FlatAppearance.BorderSize = 0;
            btnInspect.BackColor = Color.FromArgb(0, 122, 204);
            btnInspect.ForeColor = Color.White;
            btnInspect.Cursor = Cursors.Hand;
            headerPanel.Controls.Add(btnInspect);

            // 歷史回查導覽按鈕
            btnPrev = new Button();
            btnPrev.Text = "⬅️ 上一張";
            btnPrev.Size = new Size(110, 50);
            btnPrev.Location = new Point(210, 40);
            btnPrev.Font = new Font("微軟正黑體", 12, FontStyle.Bold);
            btnPrev.FlatStyle = FlatStyle.Flat;
            btnPrev.FlatAppearance.BorderSize = 0;
            btnPrev.BackColor = Color.FromArgb(70, 70, 70);
            btnPrev.ForeColor = Color.White;
            btnPrev.Cursor = Cursors.Hand;
            btnPrev.Enabled = false;
            btnPrev.Click += BtnPrev_Click;
            headerPanel.Controls.Add(btnPrev);

            btnNext = new Button();
            btnNext.Text = "下一張 ➡️";
            btnNext.Size = new Size(110, 50);
            btnNext.Location = new Point(330, 40);
            btnNext.Font = new Font("微軟正黑體", 12, FontStyle.Bold);
            btnNext.FlatStyle = FlatStyle.Flat;
            btnNext.FlatAppearance.BorderSize = 0;
            btnNext.BackColor = Color.FromArgb(70, 70, 70);
            btnNext.ForeColor = Color.White;
            btnNext.Cursor = Cursors.Hand;
            btnNext.Enabled = false;
            btnNext.Click += BtnNext_Click;
            headerPanel.Controls.Add(btnNext);

            // 暫停/繼續按鈕
            btnPauseResume = new Button();
            btnPauseResume.Text = "⏸️ 暫停";
            btnPauseResume.Size = new Size(110, 50);
            btnPauseResume.Location = new Point(450, 40);
            btnPauseResume.Font = new Font("微軟正黑體", 12, FontStyle.Bold);
            btnPauseResume.FlatStyle = FlatStyle.Flat;
            btnPauseResume.FlatAppearance.BorderSize = 0;
            btnPauseResume.BackColor = Color.Goldenrod;
            btnPauseResume.ForeColor = Color.White;
            btnPauseResume.Cursor = Cursors.Hand;
            btnPauseResume.Enabled = false;
            btnPauseResume.Click += BtnPauseResume_Click;
            headerPanel.Controls.Add(btnPauseResume);

            // 🌟 [新增] 開啟 CSV 報表按鈕
            btnOpenCsv = new Button();
            btnOpenCsv.Text = "📊 開啟報表";
            btnOpenCsv.Size = new Size(130, 50);
            btnOpenCsv.Location = new Point(570, 40); // 放在暫停按鈕的右邊
            btnOpenCsv.Font = new Font("微軟正黑體", 12, FontStyle.Bold);
            btnOpenCsv.FlatStyle = FlatStyle.Flat;
            btnOpenCsv.FlatAppearance.BorderSize = 0;
            btnOpenCsv.BackColor = Color.Purple; // 用紫色凸顯報表功能
            btnOpenCsv.ForeColor = Color.White;
            btnOpenCsv.Cursor = Cursors.Hand;
            btnOpenCsv.Enabled = false; // 初始狀態設為不可按，等跑完才解鎖
            btnOpenCsv.Click += BtnOpenCsv_Click;
            headerPanel.Controls.Add(btnOpenCsv);

            // 機台指令標籤 (因為加了報表按鈕，X 座標往右推避免重疊)
            lblAction.Font = new Font("微軟正黑體", 26, FontStyle.Bold);
            lblAction.ForeColor = Color.WhiteSmoke;
            lblAction.BackColor = Color.Transparent;
            lblAction.AutoSize = true;
            lblAction.Location = new Point(720, 20); // 往右推
            headerPanel.Controls.Add(lblAction);

            // 系統說明標籤 (X 座標同步往右推)
            lblMessage.Font = new Font("微軟正黑體", 12, FontStyle.Regular);
            lblMessage.ForeColor = Color.LightGray;
            lblMessage.BackColor = Color.Transparent;
            lblMessage.AutoSize = true;
            lblMessage.Location = new Point(725, 75); // 往右推
            headerPanel.Controls.Add(lblMessage);

            // 2. 右側面板
            Panel rightPanel = new Panel();
            rightPanel.Dock = DockStyle.Right;
            rightPanel.Width = 380;
            rightPanel.BackColor = Color.FromArgb(35, 35, 38);
            rightPanel.Padding = new Padding(20);
            this.Controls.Add(rightPanel);

            Label lblListTitle = new Label();
            lblListTitle.Text = "📜 即時檢測日誌 (Live Log)";
            lblListTitle.Font = new Font("微軟正黑體", 14, FontStyle.Bold);
            lblListTitle.ForeColor = Color.WhiteSmoke;
            lblListTitle.Dock = DockStyle.Top;
            lblListTitle.Height = 40;
            rightPanel.Controls.Add(lblListTitle);

            // 瑕疵數據列表
            lstDefects = new ListBox();
            lstDefects.Dock = DockStyle.Fill;
            lstDefects.BackColor = Color.FromArgb(20, 20, 20);
            lstDefects.ForeColor = Color.Cyan;
            lstDefects.Font = new Font("Consolas", 11, FontStyle.Regular);
            lstDefects.BorderStyle = BorderStyle.None;
            rightPanel.Controls.Add(lstDefects);
            lstDefects.BringToFront();

            // 3. 圖片顯示區
            picWafer.Dock = DockStyle.Fill;
            picWafer.SizeMode = PictureBoxSizeMode.Zoom;
            picWafer.BackColor = Color.FromArgb(15, 15, 15);

            Panel imageContainer = new Panel();
            imageContainer.Dock = DockStyle.Fill;
            imageContainer.Padding = new Padding(30);
            imageContainer.Controls.Add(picWafer);
            this.Controls.Add(imageContainer);

            // 強制圖層順序
            headerPanel.SendToBack();
            rightPanel.BringToFront();
            imageContainer.BringToFront();
        }

        // =========================================================
        // 🌟 [新增] 開啟 CSV 報表的邏輯
        // =========================================================
        private void BtnOpenCsv_Click(object sender, EventArgs e)
        {
            if (!string.IsNullOrEmpty(latestCsvPath) && File.Exists(latestCsvPath))
            {
                // 呼叫 Windows 系統預設軟體 (如 Excel) 打開該檔案
                System.Diagnostics.Process.Start(latestCsvPath);
            }
            else
            {
                MessageBox.Show("找不到 CSV 報表檔案，可能尚未產出或已被刪除！", "系統提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        // =========================================================
        // 暫停/繼續按鈕的切換邏輯
        // =========================================================
        private void BtnPauseResume_Click(object sender, EventArgs e)
        {
            isPaused = !isPaused;

            if (isPaused)
            {
                btnPauseResume.Text = "▶️ 繼續";
                btnPauseResume.BackColor = Color.SeaGreen;
                lstDefects.Items.Add(new string('-', 40));
                lstDefects.Items.Add("⏸️ [系統插斷] 產線已暫停 (機台 Hold 批)");
                lstDefects.Items.Add(new string('-', 40));
            }
            else
            {
                btnPauseResume.Text = "⏸️ 暫停";
                btnPauseResume.BackColor = Color.Goldenrod;
                lstDefects.Items.Add("▶️ [系統插斷] 解除暫停，恢復進片檢測...");
                lstDefects.Items.Add(new string('-', 40));
            }

            // 畫面捲到最下面
            lstDefects.TopIndex = lstDefects.Items.Count - 1;
        }

        // =========================================================
        // 批次執行迴圈 (加入了暫停等待機制)
        // =========================================================
        private async void btnInspect_Click(object sender, EventArgs e)
        {
            using (FolderBrowserDialog folderDialog = new FolderBrowserDialog())
            {
                folderDialog.Description = "請選擇包含待測晶圓影像的資料夾";

                if (folderDialog.ShowDialog() == DialogResult.OK)
                {
                    string folderPath = folderDialog.SelectedPath;

                    List<string> imageFiles = new List<string>();
                    string[] extensions = { "*.jpg", "*.jpeg", "*.png", "*.bmp" };
                    foreach (string ext in extensions)
                    {
                        imageFiles.AddRange(Directory.GetFiles(folderPath, ext, SearchOption.TopDirectoryOnly));
                    }

                    if (imageFiles.Count == 0)
                    {
                        MessageBox.Show("該資料夾中找不到任何圖片！", "系統提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                        return;
                    }

                    imageFiles.Sort();

                    // 初始化狀態與記憶庫
                    btnInspect.Enabled = false;
                    btnPrev.Enabled = false;
                    btnNext.Enabled = false;
                    btnOpenCsv.Enabled = false; // 🌟 [新增] 執行中鎖住報表按鈕
                    latestCsvPath = "";         // 🌟 [新增] 清空舊路徑

                    // 啟用暫停按鈕並重置狀態
                    isPaused = false;
                    btnPauseResume.Enabled = true;
                    btnPauseResume.Text = "⏸️ 暫停";
                    btnPauseResume.BackColor = Color.Goldenrod;

                    reviewHistory.Clear();
                    currentReviewIndex = -1;

                    // 🌟 初始化 CSV 暫存區，寫入標題列
                    csvDataLines.Clear();
                    csvDataLines.Add("Wafer_Image,Defect_ID,Class,Measurement,Area (um^2),Center_X (px),Center_Y (px)");

                    lstDefects.Items.Clear();
                    lstDefects.Items.Add($"🚀 系統啟動：批次載入 {imageFiles.Count} 片晶圓");
                    lstDefects.Items.Add(new string('=', 40));

                    for (int i = 0; i < imageFiles.Count; i++)
                    {
                        // 非同步暫停檢查 (不會卡死視窗！)
                        while (isPaused)
                        {
                            await Task.Delay(200);
                        }

                        string filePath = imageFiles[i];
                        string fileName = Path.GetFileName(filePath);

                        lblAction.Text = $"檢測中 ({i + 1}/{imageFiles.Count})...";
                        lblAction.ForeColor = Color.DeepSkyBlue;
                        lblMessage.Text = $"系統說明: 正在將 {fileName} 送入 AI 模組...";

                        await InspectWaferAsync(filePath);

                        lstDefects.TopIndex = lstDefects.Items.Count - 1;
                        await Task.Delay(1200);
                    }

                    // 批次結束，關閉暫停按鈕並開啟回查功能
                    lblAction.Text = "✅ 批次檢測完成";
                    lblAction.ForeColor = Color.LimeGreen;

                    // 🌟 [新增] 匯出 CSV 報表 (只要有資料就匯出)
                    if (csvDataLines.Count > 1)
                    {
                        string csvFileName = $"Batch_Report_{DateTime.Now:yyyyMMdd_HHmmss}.csv";
                        string csvFilePath = Path.Combine(tempDir, csvFileName);
                        // 使用 UTF8 (加上 BOM)，確保 Excel 打開時中文不會變成亂碼
                        File.WriteAllLines(csvFilePath, csvDataLines, new System.Text.UTF8Encoding(true));
                        lstDefects.Items.Add($"💾 CSV報表已匯出: {csvFileName}");

                        // 🌟 [新增] 記錄路徑，並解鎖開啟按鈕
                        latestCsvPath = csvFilePath;
                        btnOpenCsv.Enabled = true;
                    }

                    lblMessage.Text = "系統說明: 掃描完畢，機台進入待機。可使用上方導覽按鈕回查紀錄。";
                    btnInspect.Enabled = true;
                    btnPauseResume.Enabled = false;
                    UpdateButtonStates();
                }
            }
        }

        // =========================================================
        // 解析 API 結果並寫入記憶庫
        // =========================================================
        private async Task InspectWaferAsync(string filePath)
        {
            try
            {
                using (HttpClient client = new HttpClient())
                using (MultipartFormDataContent content = new MultipartFormDataContent())
                using (FileStream fileStream = new FileStream(filePath, FileMode.Open, FileAccess.Read))
                {
                    StreamContent streamContent = new StreamContent(fileStream);
                    streamContent.Headers.Add("Content-Type", "application/octet-stream");
                    content.Add(streamContent, "file", Path.GetFileName(filePath));

                    HttpResponseMessage response = await client.PostAsync(apiUrl, content);
                    response.EnsureSuccessStatusCode();

                    string responseBody = await response.Content.ReadAsStringAsync();
                    JObject json = JObject.Parse(responseBody);

                    if (json["status"].ToString() == "error")
                    {
                        lstDefects.Items.Add($"❌ {Path.GetFileName(filePath)} 檢測失敗");
                        return;
                    }

                    string action = json["fdc_action"].ToString();
                    string message = json["fdc_message"].ToString();
                    string filename = json["filename"].ToString();

                    string actionText = "";
                    Color actionColor = Color.White;

                    if (action == "STOP")
                    {
                        actionText = $"🚨 機台指令: {action}";
                        actionColor = Color.Red;
                        lstDefects.Items.Add($"▶ [Wafer] {filename} => 🚨 {action}");
                    }
                    else if (action == "ALARM")
                    {
                        actionText = $"⚠️ 機台指令: {action}";
                        actionColor = Color.DarkOrange;
                        lstDefects.Items.Add($"▶ [Wafer] {filename} => ⚠️ {action}");
                    }
                    else
                    {
                        actionText = $"✅ 機台指令: {action}";
                        actionColor = Color.LimeGreen;
                        lstDefects.Items.Add($"▶ [Wafer] {filename} => ✅ {action}");
                    }

                    JArray defectsArray = (JArray)json["defects_list"];
                    if (defectsArray.Count == 0) lstDefects.Items.Add("   (無瑕疵)");
                    else foreach (var defect in defectsArray) lstDefects.Items.Add($"   {defect.ToString()}");
                    lstDefects.Items.Add(new string('-', 40));

                    // 🌟 解析給 CSV 用的原始數據，寫入暫存清單
                    if (json["raw_defects"] is JArray rawDefectsArray)
                    {
                        foreach (var d in rawDefectsArray)
                        {
                            // 組合逗號分隔字串
                            string line = $"{filename},{d["Defect_ID"]},{d["Class"]},\"{d["Measurement"]}\",{d["Area_um2"]},{d["Center_X"]},{d["Center_Y"]}";
                            csvDataLines.Add(line);
                        }
                    }

                    string annotatedImgName = $"result_V13_16_Annotated_{filename}";
                    string annotatedImgPath = Path.Combine(tempDir, annotatedImgName);

                    WaferRecord record = new WaferRecord
                    {
                        FileName = filename,
                        AnnotatedImagePath = annotatedImgPath,
                        ActionText = actionText,
                        ActionColor = actionColor,
                        Message = $"系統說明: {message}"
                    };
                    reviewHistory.Add(record);
                    currentReviewIndex = reviewHistory.Count - 1;

                    ShowHistoryRecord(currentReviewIndex);
                }
            }
            catch (Exception ex)
            {
                lblAction.Text = "網路斷線或伺服器異常";
                lblAction.ForeColor = Color.Red;
                lstDefects.Items.Add($"❌ 連線失敗: {ex.Message}");
            }
        }

        // =========================================================
        // 歷史回查控制邏輯
        // =========================================================
        private void BtnPrev_Click(object sender, EventArgs e)
        {
            if (currentReviewIndex > 0)
            {
                currentReviewIndex--;
                ShowHistoryRecord(currentReviewIndex);
            }
        }

        private void BtnNext_Click(object sender, EventArgs e)
        {
            if (currentReviewIndex < reviewHistory.Count - 1)
            {
                currentReviewIndex++;
                ShowHistoryRecord(currentReviewIndex);
            }
        }

        // 🌟 加入找不到圖時的防呆清空機制
        private void ShowHistoryRecord(int index)
        {
            if (index < 0 || index >= reviewHistory.Count) return;
            WaferRecord record = reviewHistory[index];

            lblAction.Text = record.ActionText;
            lblAction.ForeColor = record.ActionColor;
            lblMessage.Text = record.Message;

            if (File.Exists(record.AnnotatedImagePath))
            {
                using (FileStream fs = new FileStream(record.AnnotatedImagePath, FileMode.Open, FileAccess.Read))
                {
                    picWafer.Image = Image.FromStream(fs);
                }
            }
            else
            {
                // 如果找不到新圖片，強制清空畫面，破除上一張圖的殘影！
                picWafer.Image = null;
                lblMessage.Text += " (⚠️ 警告：無法載入標註影像)";
            }

            UpdateButtonStates();
        }

        private void UpdateButtonStates()
        {
            btnPrev.Enabled = (currentReviewIndex > 0);
            btnNext.Enabled = (currentReviewIndex < reviewHistory.Count - 1);
        }
    }
}