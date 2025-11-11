from typing import List, Dict, Any, Optional
import socket
import json
import threading
import time
import sys
import pyperclip

from translate_word import translate_word


# --- AYARLAR ---
# Kelime boyutlarını tahmin etmek için (ASS oluştururken kullandığınız değerlerle uyumlu olmalı)
EST_CHAR_WIDTH = 90   # 4K'da 120 punto için yaklaşık karakter genişliği
EST_LINE_HEIGHT = 120 # Satır yüksekliği

class ASSHandler():
    def __init__(self) -> None:
        self.file_path = "./subtitle.ass"
        # Kelimeleri düz bir liste olarak tutmak, anlık tarama için daha verimlidir.
        self.word_list: List[Dict[str, Any]] = []
        
    def time_to_seconds(self, ts: str) -> float:
        """ASS zaman damgasını (H:MM:SS.cs) saniyeye (float) çevirir."""
        try:
            h, m, s_cs = ts.split(':')
            s, cs = s_cs.split('.')
            return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100.0
        except ValueError:
            return 0.0

    def generate_words(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                file_content = f.readlines()
        except FileNotFoundError:
            print(f"UYARI: {self.file_path} bulunamadı. Kelime listesi boş.")
            return

        for line in file_content:
            if not line.startswith("Dialogue:"):
                continue
            
            try:
                # Daha sağlam bir parse işlemi
                parts = line.split(",", 9) # İlk 9 virgülü ayır
                if len(parts) < 10: continue
                
                start_ts = parts[1]
                end_ts = parts[2]
                raw_text = parts[9]
                
                # {\pos(x,y)}Kelime formatını ayıkla
                # Basit bir string parse yaklaşımı (sizin formatınıza uygun)
                if "\\pos(" in raw_text:
                    pos_part, word_text = raw_text.split(")}", 1)
                    pos_part = pos_part.split("\\pos(", 1)[1]
                    pos_x_str, pos_y_str = pos_part.split(",", 1)
                    
                    pos_x = int(pos_x_str)
                    pos_y = int(pos_y_str)
                    word_text = word_text.strip()

                    # Kelimenin tahmini genişlik ve yüksekliğini hesapla
                    width = len(word_text) * EST_CHAR_WIDTH
                    height = EST_LINE_HEIGHT

                    self.word_list.append({
                        "start": self.time_to_seconds(start_ts),
                        "end": self.time_to_seconds(end_ts),
                        "x1": pos_x,
                        "y1": pos_y,            # \an7 varsayımıyla üst kenar
                        "x2": pos_x + width,    # Sağ kenar
                        "y2": pos_y + height,   # Alt kenar
                        "text": word_text
                    })
            except Exception as e:
                print(f"Satır parse hatası: {line.strip()} -> {e}")
                continue

        print(f"ASSHandler: {len(self.word_list)} kelime yüklendi.")

    def copy_current_subtitle(self, current_time: int):
        word_str = ''
        for word in self.word_list:
            if word["start"] <= current_time <= word["end"]:
                word_str += word['text'] + ' '
        pyperclip.copy(word_str)
        
        

class MpvIPC:
    def __init__(self, ass_handler: ASSHandler, ipc_path="/tmp/mpvsocket"):
        self.ipc_path = ipc_path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.is_running = True
        self.ass_handler = ass_handler
        
        self.current_time = -1.0
        self.current_x = -1
        self.current_y = -1
        
        # Sürekli aynı kelimeyi tekrar tekrar yollamamak için son durumu hatırlayalım
        self.last_hovered_word = None 
        
        try:
            self.sock.connect(self.ipc_path)
            print(f"Bağlantı başarılı: {self.ipc_path}")
        except FileNotFoundError:
            print(f"HATA: {self.ipc_path} soketi bulunamadı.")
            print("mpv'yi '--input-ipc-server=/tmp/mpvsocket' ile başlattınız mı?")
            sys.exit(1)

        self.listener = threading.Thread(target=self._listener_loop, daemon=True)
        self.listener.start()

    def _listener_loop(self):
        buffer = ""
        while self.is_running:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data: break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self._handle_event(json.loads(line))
            except Exception as e:
                if self.is_running: print(f"Dinleyici hatası: {e}")
                break
        print("Dinleyici kapandı.")

    def _handle_event(self, event):
        evt_type = event.get("event")
        if evt_type == "property-change":
            prop_name = event.get("name")
            value = event.get("data")

            if prop_name == "time-pos" and value is not None:
                self.current_time = float(value)
                # Zaman değiştiğinde de overlap kontrolü yapmalıyız 
                # (fare sabit dururken altına yeni kelime gelebilir)
                self.process_overlap()
            
            elif prop_name == "mouse-pos" and value and 'x' in value:
                self.current_x = value['x']
                self.current_y = value['y']
                self.process_overlap()

        elif evt_type == "client-message":
            args = event.get("args", [])
            if len(args) > 0 and args[0] == "python-copy-trigger":
                self.ass_handler.copy_current_subtitle(self.current_time)
                
        elif evt_type == "shutdown":
             print("mpv kapandı.")
             self.is_running = False

    def process_overlap(self):
        """
        Anlık zaman ve fare konumuna göre hangi kelimenin üzerinde olduğumuzu bulur.
        """
        if self.current_time < 0 or self.current_x < 0:
            return

        hovered = None
        
        # Basit bir döngü ile kontrol (kelime sayısı çok artarsa optimize edilebilir)
        for word in self.ass_handler.word_list:
            # 1. Zaman kontrolü: Kelime şu an ekranda mı?
            if word["start"] <= self.current_time <= word["end"]:
                # 2. Konum kontrolü: Fare kelimenin kutusu içinde mi?
                # (\an7 varsayımıyla: x1=sol, y1=üst, x2=sağ, y2=alt)
                if (word["x1"] <= self.current_x <= word["x2"] and 
                    word["y1"] <= self.current_y <= word["y2"]):
                    hovered = word
                    break # İlk bulunan kelimeyi al
        
        # Durum değişikliği varsa mpv'ye bildir
        if hovered != self.last_hovered_word:
            self.last_hovered_word = hovered
            if hovered:
                print(f"Üzerine gelindi: {hovered['text']}")
                # Bulunan kelimeyi ekrana yazdır (kalıcı değil, kısa süreli)
                # Kelimenin biraz üstüne yazdıralım ki kelimeyi kapatmasın
                text = translate_word(hovered['text'])
                self.show_text_at_pos(f"{text}", 50, 70, font_size=40)
                self.pause_video()
            else:
                # Fare boşluğa çıktıysa ekrandaki yazıyı temizle
                # self.clear_text() # İsterseniz açabilirsiniz, bazen çok yanıp sönme yapabilir.
                self.resume_video()
                self.clear_text()

    def send_command(self, command_list):
        if not self.is_running: return
        try:
            message = json.dumps({"command": command_list}) + "\n"
            self.sock.sendall(message.encode('utf-8'))
        except BrokenPipeError:
            self.is_running = False

    def start_observing(self):
        print("Özellik takibi başlatılıyor...")
        self.send_command(["observe_property", 1, "time-pos"])
        self.send_command(["observe_property", 2, "mouse-pos"])
        self.send_command(["keybind", "ctrl+c", "script-message python-copy-trigger"])
        
    def _show_text_at_pos(self, text, x, y, font_size=40):
        """
        Ekranda istenilen yere SİYAH ARKA PLANLI yazı yazar.
        """
        prefix = "${osd-ass-cc/0}"
        # \bord5: Kalın siyah kenarlık (neredeyse kutu gibi görünür)
        # \3c&H000000&: Kenarlık rengi tam siyah
        # \1c&HFFFFFF&: Metin rengi tam beyaz
        # \alpha&H00&: Tam opak
        style = r"{\an7\bord5\3c&H000000&\1c&HFFFFFF&\alpha&H00&}"
        pos_tag = r"{\fs" + str(font_size) + r"\pos(" + str(int(x)) + r"," + str(int(y)) + r")}"
        
        final_text = prefix + style + pos_tag + text
        self.send_command(["show-text", final_text, 3600000, 1])


    def show_text_at_pos(self, text, x, y, font_size=20):
        """
        Lua köprüsü üzerinden ekrana SİYAH ARKA PLANLI yazı yazar.
        """
        # script-message komutuyla Lua'daki fonksiyonu çağırıyoruz.
        # Argümanlar string olarak gitmeli.
        self.send_command([
            "script-message", 
            "show-ass-text", 
            str(int(x)), 
            str(int(y)), 
            str(font_size), 
            text
        ])

    def clear_text(self):
        """Lua köprüsü üzerinden yazıyı temizler (boş metin göndererek)."""
        # Koordinat ve font boyutu önemli değil, sadece boş metin gönderiyoruz.
        self.send_command(["script-message", "show-ass-text", "0", "0", "0", ""])
        
    def _clear_text(self):
        self.send_command(["show-text", "", 0, 1])

    def pause_video(self):
        """Videoyu duraklatır."""
        print("Video duraklatılıyor...")
        self.send_command(["set_property", "pause", True])

    def resume_video(self):
        """Videoyu devam ettirir."""
        print("Video devam ettiriliyor...")
        self.send_command(["set_property", "pause", False])

        
# --- KULLANIM ÖRNEĞİ ---
if __name__ == "__main__":
    ass = ASSHandler()
    ass.generate_words()
    
    mpv = MpvIPC(ass)
    mpv.start_observing()

    try:
        while mpv.is_running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Kapatılıyor...")
        mpv.is_running = False
