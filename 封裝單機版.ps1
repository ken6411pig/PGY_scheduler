# 建立完整 Streamlit 單機版；完成檔案在 dist\standalone-scheduler.exe。
$py = "C:\Users\YUHSIN\AppData\Local\Programs\Python\Python312\python.exe"

& $py -m PyInstaller --noconfirm --clean --onefile `
  --name "standalone-scheduler" `
  --add-data "排班器.py;." `
  --collect-all streamlit `
  --collect-binaries ortools `
  --hidden-import openpyxl `
  --hidden-import openpyxl.styles `
  --hidden-import ortools.sat.python.cp_model `
  --hidden-import docx `
  --hidden-import docx.oxml `
  --hidden-import docx.enum.table `
  --hidden-import docx.enum.text `
  --exclude-module torch `
  --exclude-module torchvision `
  --exclude-module torchaudio `
  --exclude-module tensorflow `
  --exclude-module cv2 `
  --exclude-module pyarrow `
  --exclude-module transformers `
  "單機版排班器.py"
