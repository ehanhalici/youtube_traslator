
#!/bin/bash

# 1. Argüman kontrolü: URL ve girdi dosyası adı verilmiş mi?
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Kullanım: $0 <youtube_url> <girdi_dosyasi_adi>"
    echo "Örnek: $0 https://youtu.be/0o8Ex8mXigU timedtext"
    exit 1
fi

YOUTUBE_URL="$1"
INPUT_NAME="$2"

# 2. Altyazıyı oluştur
echo "Altyazı oluşturuluyor ($INPUT_NAME kullanılarak)..."
python3 cut_analysis.py "$INPUT_NAME" > subtitle.ass

if [ $? -ne 0 ]; then
    echo "HATA: subtitle.ass oluşturulamadı. Python scripti hata verdi."
    exit 1
fi

# 3. mpv'yi başlat
echo "mpv başlatılıyor: $YOUTUBE_URL"
mpv "$YOUTUBE_URL" \
    --input-ipc-server=/tmp/mpvsocket \
    --sub-file="$(pwd)/subtitle.ass" \
    --sub-create-cc-track=yes \
    --msg-level=all=v
