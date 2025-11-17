
#!/bin/bash

# 1. Argüman kontrolü: URL ve girdi dosyası adı verilmiş mi?
if [ -z "$1" ]; then
    echo "Kullanım: $0 <youtube_url>"
    echo "Örnek: $0 https://youtu.be/0o8Ex8mXigU"
    exit 1
fi

YOUTUBE_URL="$1"

# 2. Altyazıyı oluştur
echo "Altyazı oluşturuluyor ($INPUT_NAME kullanılarak)..."
uv run cut_analysis.py "$YOUTUBE_URL" > subtitle.ass

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
