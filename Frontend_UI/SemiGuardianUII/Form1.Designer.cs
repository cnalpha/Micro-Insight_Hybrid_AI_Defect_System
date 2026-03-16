namespace SemiGuardianUII
{
    partial class Form1
    {
        /// <summary>
        /// 設計工具所需的變數。
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// 清除任何使用中的資源。
        /// </summary>
        /// <param name="disposing">如果應該處置受控資源則為 true，否則為 false。</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form 設計工具產生的程式碼

        /// <summary>
        /// 此為設計工具支援所需的方法 - 請勿使用程式碼編輯器修改
        /// 這個方法的內容。
        /// </summary>
        private void InitializeComponent()
        {
            this.btnInspect = new System.Windows.Forms.Button();
            this.backgroundWorker1 = new System.ComponentModel.BackgroundWorker();
            this.lblAction = new System.Windows.Forms.Label();
            this.lblMessage = new System.Windows.Forms.Label();
            this.picWafer = new System.Windows.Forms.PictureBox();
            ((System.ComponentModel.ISupportInitialize)(this.picWafer)).BeginInit();
            this.SuspendLayout();
            // 
            // btnInspect
            // 
            this.btnInspect.Location = new System.Drawing.Point(12, 12);
            this.btnInspect.Name = "btnInspect";
            this.btnInspect.Size = new System.Drawing.Size(145, 75);
            this.btnInspect.TabIndex = 0;
            this.btnInspect.Text = "載入晶圓並檢測";
            this.btnInspect.UseVisualStyleBackColor = true;
            this.btnInspect.Click += new System.EventHandler(this.btnInspect_Click);
            // 
            // lblAction
            // 
            this.lblAction.AutoSize = true;
            this.lblAction.Font = new System.Drawing.Font("新細明體", 24F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(136)));
            this.lblAction.Location = new System.Drawing.Point(416, 154);
            this.lblAction.Name = "lblAction";
            this.lblAction.Size = new System.Drawing.Size(284, 40);
            this.lblAction.TabIndex = 1;
            this.lblAction.Text = "等待晶圓進站...";            
            // 
            // lblMessage
            // 
            this.lblMessage.AutoSize = true;
            this.lblMessage.Location = new System.Drawing.Point(420, 27);
            this.lblMessage.Name = "lblMessage";
            this.lblMessage.Size = new System.Drawing.Size(75, 15);
            this.lblMessage.TabIndex = 2;
            this.lblMessage.Text = "系統說明: ";
            // 
            // picWafer
            // 
            this.picWafer.Location = new System.Drawing.Point(12, 113);
            this.picWafer.Name = "picWafer";
            this.picWafer.Size = new System.Drawing.Size(377, 338);
            this.picWafer.SizeMode = System.Windows.Forms.PictureBoxSizeMode.Zoom;
            this.picWafer.TabIndex = 3;
            this.picWafer.TabStop = false;
            // 
            // Form1
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(8F, 15F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(917, 484);
            this.Controls.Add(this.picWafer);
            this.Controls.Add(this.lblMessage);
            this.Controls.Add(this.lblAction);
            this.Controls.Add(this.btnInspect);
            this.Name = "Form1";
            this.Text = "等待晶圓進站...";
            ((System.ComponentModel.ISupportInitialize)(this.picWafer)).EndInit();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.Button btnInspect;
        private System.ComponentModel.BackgroundWorker backgroundWorker1;
        private System.Windows.Forms.Label lblAction;
        private System.Windows.Forms.Label lblMessage;
        private System.Windows.Forms.PictureBox picWafer;
    }
}

