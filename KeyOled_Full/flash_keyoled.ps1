# =============================================================================
#  flash_keyoled.ps1 —— KeyOled_Full 一键烧录 + 自动验证
#
#  双击同目录的 flash_keyoled.bat 即可，不要手动改这个文件里的路径。
#
#  做四件事：
#      1. 关掉可能占着调试器的 Keil (UV4)
#      2. 把 Project\Objects\KeyOled_Full.hex 烧进板子
#      3. 复位，从 RAM 读回 OLED 显存，确认第一屏是「李登辉」
#      4. 模拟按一次 KEY1，再读回显存，确认切成「叫爸爸」
#
#  两点说明：
#   - 第 4 步走的是"直接操作 GPIOG 寄存器把 PG3 拉低"，
#     按键在硬件上就是 PG3 -- 按键 -- GND，拉低 == 按下，电气上完全一致。
#   - 本机有两套 python，各缺一样东西，所以读和渲染分两步走：
#       $PY_EMB 有 pyocd 没 Pillow   -> 负责从板上读
#       $PY_PIL 有 Pillow 没 pyocd   -> 负责把读回的显存渲染成图
# =============================================================================

$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$PY_EMB = 'D:\STM32_AI_Tools\venvs\emb\Scripts\python.exe'
$PY_PIL = 'C:\Users\y7000\.workbuddy-ai\binaries\python\envs\default\Scripts\python.exe'
$HEX    = Join-Path $here 'Project\Objects\KeyOled_Full.hex'
$UID    = '37FF71064E5734360B791543'
$WORK   = 'D:\STM32_Project'
$VER    = Join-Path $WORK '_keyoled_verify.py'
$SIM    = Join-Path $WORK '_key_sim.py'

function Say($t) { Write-Host ''; Write-Host ('=== ' + $t + ' ===') -ForegroundColor Cyan }

Say '0/5 环境自检'
foreach ($f in @($PY_EMB, $PY_PIL, $HEX, $VER, $SIM)) {
    if (-not (Test-Path $f)) {
        Write-Host ('缺少文件: ' + $f) -ForegroundColor Red
        Write-Host '按回车关闭...'; [void][Console]::ReadLine(); exit 1
    }
}
Write-Host ('hex  : ' + $HEX)
Write-Host ('size : ' + (Get-Item $HEX).Length + ' bytes')

Say '1/5 关闭可能占用调试器的 Keil'
$uv = Get-Process UV4 -ErrorAction SilentlyContinue
if ($uv) { $uv | Stop-Process -Force; Write-Host '已关闭 UV4'; Start-Sleep -Seconds 1 }
else { Write-Host 'UV4 未运行' }

Say '2/5 烧录固件'
& $PY_EMB -m pyocd flash -t stm32f103ze -u $UID --format hex $HEX
if ($LASTEXITCODE -ne 0) {
    Write-Host ''
    Write-Host '烧录失败。常见原因：' -ForegroundColor Red
    Write-Host '  - ST-Link 与板子的 SWD 排线松了 / 没插'
    Write-Host '  - 板子没上电'
    Write-Host '  - 串口助手 / Keil 调试会话还占着调试器'
    Write-Host '处理：把板子 USB 拔掉重插一次，再双击本文件。'
    Write-Host ''
    Write-Host '按回车关闭...'; [void][Console]::ReadLine(); exit 2
}
Write-Host '烧录成功' -ForegroundColor Green

$dumpA = Join-Path $WORK '_gram_poweron.bin'
$dumpB = Join-Path $WORK '_gram_after_key1.bin'

Say '3/5 复位并读回显存（期望：李登辉）'
& $PY_EMB $VER --read --reset --dump $dumpA
& $PY_PIL $VER --render $dumpA --tag poweron

Say '4/5 模拟按一次 KEY1，再读回显存（期望：叫爸爸）'
& $PY_EMB $SIM 1
& $PY_EMB $VER --read --no-strings --dump $dumpB
& $PY_PIL $VER --render $dumpB --tag after_key1

Say '5/5 结论'
$chk = @"
import hashlib,sys
m=lambda p: hashlib.md5(open(p,'rb').read()).hexdigest()
a,b=m(r'$dumpA'),m(r'$dumpB')
print('上电屏 md5 :',a)
print('按KEY1后   :',b)
print('两屏不同   :',a!=b,'  <- 期望 True')
sys.exit(0 if a!=b else 3)
"@
& $PY_PIL -c $chk

Write-Host ''
Write-Host '两张读回图在 D:\STM32_Project\ 下：' -ForegroundColor Green
Write-Host '  _oled_readback_poweron.png    上电第一屏'
Write-Host '  _oled_readback_after_key1.png 按 KEY1 之后'
Write-Host ''
Write-Host '也可以直接看板子上的 OLED 屏，效果应当一致。'
Write-Host ''
Write-Host '按回车关闭...'
[void][Console]::ReadLine()
