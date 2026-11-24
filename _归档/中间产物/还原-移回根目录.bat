@echo off
chcp 936 >nul
echo 正在把中间产物目录移回 D:\STM32_Project ...
move /y "__pycache__" "D:\STM32_Project\__pycache__"
move /y "_ir_scan_data" "D:\STM32_Project\_ir_scan_data"
move /y "_led_render" "D:\STM32_Project\_led_render"
move /y "_pkg_artifacts_backup" "D:\STM32_Project\_pkg_artifacts_backup"
move /y "_preview_0918" "D:\STM32_Project\_preview_0918"
move /y "_pv" "D:\STM32_Project\_pv"
move /y "_sch_render" "D:\STM32_Project\_sch_render"
move /y "_tmp_build_junk" "D:\STM32_Project\_tmp_build_junk"
move /y "_视频抽帧" "D:\STM32_Project\_视频抽帧"
move /y "sch_crop" "D:\STM32_Project\sch_crop"
echo 完成
pause
