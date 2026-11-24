@echo off
echo 请先完全退出帝国时代4。每个订阅模组只保留最新的 .sga，旧版本移到 mods_old 文件夹。
pause
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'My Games\Age of Empires IV\mods\extension\subscriptions'; $o=Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'My Games\Age of Empires IV\mods_old'; Get-ChildItem $s -Directory | ForEach-Object { $f=@(Get-ChildItem $_.FullName -Filter *.sga | Sort-Object LastWriteTime -Descending); if($f.Count -gt 1){ $d=Join-Path $o $_.Name; New-Item -ItemType Directory -Force $d | Out-Null; $f | Select-Object -Skip 1 | ForEach-Object { Write-Host ('moved ' + $_.FullName); Move-Item $_.FullName $d -Force } } }"
echo 完成。
pause
