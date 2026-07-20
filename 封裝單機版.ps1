# Build the standalone Streamlit scheduler. Output: dist\standalone-scheduler.exe
$py = "C:\Users\YUHSIN\AppData\Local\Programs\Python\Python312\python.exe"
$root = $PSScriptRoot
$app = Get-ChildItem -LiteralPath $root -Filter "*.py" | Where-Object { (Get-Content -LiteralPath $_.FullName -Raw) -match "st\.set_page_config" }
if ($app.Count -ne 1) { throw "Could not locate exactly one scheduler app" }

& $py -m PyInstaller --noconfirm --clean --onefile `
  --name "standalone-scheduler" `
  --add-data "$($app[0].FullName);." `
  --collect-all streamlit `
  --collect-all pyarrow `
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
  --exclude-module transformers `
  "$root\standalone_launcher.py"
