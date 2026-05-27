@echo off
chcp 65001 >nul
echo.
echo ================================================
echo   📦 Build LeadGenTool - Đóng gói để gửi
echo ================================================
echo.

:: Bước 1: Build exe
echo [1/3] Building exe...
pyinstaller --noconfirm --onedir --add-data "*.py;." --name "LeadGenTool" tool.py
if errorlevel 1 (
    echo ❌ Build thất bại! Kiểm tra lại.
    pause
    exit /b 1
)
echo ✅ Build xong.
echo.

:: Bước 2: Copy các file .py cần thiết vào dist
echo [2/3] Copy files...
set DEST=dist\LeadGenTool

copy filter.py          %DEST%\ >nul
copy scorer.py          %DEST%\ >nul
copy enricher.py        %DEST%\ >nul
copy extractor.py       %DEST%\ >nul
copy exporter.py        %DEST%\ >nul
copy email_templates.py %DEST%\ >nul
copy industries.py      %DEST%\ >nul
copy ai_filter.py       %DEST%\ >nul 2>nul

:: Copy .env nếu có
if exist .env copy .env %DEST%\ >nul

:: Tạo file hướng dẫn
echo # Hướng dẫn sử dụng LeadGenTool > %DEST%\HUONG_DAN.txt
echo. >> %DEST%\HUONG_DAN.txt
echo 1. Double-click vào LeadGenTool.exe >> %DEST%\HUONG_DAN.txt
echo 2. Mở browser, gõ: http://localhost:5000 >> %DEST%\HUONG_DAN.txt
echo 3. Chọn ngành → Bấm Bắt đầu crawl >> %DEST%\HUONG_DAN.txt
echo 4. Sau khi crawl xong → Tab Filter → Lọc leads >> %DEST%\HUONG_DAN.txt
echo 5. Tab Email → Gen cold email → Export Excel >> %DEST%\HUONG_DAN.txt
echo. >> %DEST%\HUONG_DAN.txt
echo LƯU Ý: Giữ nguyên cửa sổ đen khi dùng tool. >> %DEST%\HUONG_DAN.txt
echo Tắt cửa sổ đen = tắt tool. >> %DEST%\HUONG_DAN.txt

echo ✅ Copy xong.
echo.

:: Bước 3: Zip lại
echo [3/3] Đóng gói ZIP...
set ZIPNAME=LeadGenTool_v5.zip

:: Xóa zip cũ nếu có
if exist %ZIPNAME% del %ZIPNAME%

:: Dùng PowerShell để zip
powershell -command "Compress-Archive -Path 'dist\LeadGenTool\*' -DestinationPath '%ZIPNAME%' -Force"
if errorlevel 1 (
    echo ⚠️  Zip thất bại, nhưng folder dist\LeadGenTool\ đã sẵn sàng.
    echo    Tự zip thủ công rồi gửi cho nhân viên.
) else (
    echo ✅ Đã tạo: %ZIPNAME%
    echo.
    echo ================================================
    echo   🎉 XONG! Gửi file %ZIPNAME% cho nhân viên.
    echo   Họ chỉ cần: Unzip → Double-click LeadGenTool.exe
    echo ================================================
)
echo.
pause