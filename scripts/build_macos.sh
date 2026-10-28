#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Darwin ]]; then
  echo '只能在 macOS 上构建真正的 .app 和 .dmg。' >&2
  exit 1
fi
arch="$(uname -m)"
python -m PyInstaller --noconfirm --clean --windowed --name StatMate \
  --osx-bundle-identifier org.statmate.desktop --target-architecture "$arch" \
  --add-data "LICENSE:." --add-data "README.md:." \
  --paths . --collect-all pyreadstat --collect-all statsmodels \
  --hidden-import openpyxl --hidden-import xlrd scripts/launch.py
/usr/libexec/PlistBuddy -c 'Set :NSHighResolutionCapable true' dist/StatMate.app/Contents/Info.plist
# Ad-hoc signature allows local loading, but is NOT a Developer ID signature or notarization.
codesign --force --deep --sign - dist/StatMate.app
codesign --verify --deep --strict dist/StatMate.app
mkdir -p build/dmg
cp -R dist/StatMate.app build/dmg/
ln -s /Applications build/dmg/Applications
hdiutil create -volname StatMate -srcfolder build/dmg -ov -format UDZO "dist/StatMate-macOS-${arch}.dmg"
