import sys
import json
from typing import List, Dict
from dataclasses import dataclass

from copy import deepcopy as copy
from subtitle_downloader import download_subtitle
@dataclass
class Word:
    key: str
    start_ms: int
    duration: int

word_list: List[Word] = []
sentences_list: List[List[Word]] = []

colors = ["\033[32;1;4m", "\033[34;1;4m"]
colors = [""]
char_time = 50
stop_time = 400
pass_parse_ms_count = 20

def load_subtitle(file_name: str):
    fp = open(file_name, "r")
    fc = fp.read()
    return json.loads(fc)

def process_events(events: List[Dict]):
    #print("Duration ms, ", events[0]["dDurationMs"])
    for block in events[1:]:
        start_block = block["tStartMs"]
        for segment in block["segs"]:
            key = segment["utf8"].strip()
            if key == "\n" or len(key) == 0:
                continue
            word_list.append(Word(key=key, start_ms=start_block + segment.get("tOffsetMs", 0), duration=-1))

def calc_duration():
    for i in range(len(word_list)-1, 0, -1 ):
        word_list[i-1].duration = word_list[i].start_ms - word_list[i-1].start_ms

def calc_time_period(ms: int) -> str:
    h = ms // 3_600_000
    ms %= 3_600_000
    
    m = ms // 60_000
    ms %= 60_000
    
    s = ms // 1000
    ms %= 1000
    
    # Milisaniyeyi (ms) 10'a bölerek saniyenin yüzde birini (cs) buluruz.
    cs = ms // 10
    
    return f"{h:01}:{m:02}:{s:02}.{cs:02}"

PIXEL_PER_CHAR_MULTIPLIER_X = 50
SPACE_WIDTH = PIXEL_PER_CHAR_MULTIPLIER_X * 1 # Kelime arasına koyacağımız boşluk (piksel)
MAX_CHAR_PER_LINE = 50
SCREEN_X = 3840
SCREEN_Y = 2160
PADDING = 400
CHAR_PIXEL = 100

def calculate_approx_width(word_text: str) -> int:
    """
    Verilen kelime ve font boyutu için yaklaşık piksel genişliğini tahmin eder.
    (PlayResX: 3840 ve Fontsize: 60 için)
    """
    # Genişliği karakter sayısı * yaklaşık piksel çarpanı olarak hesapla

    return len(word_text) * PIXEL_PER_CHAR_MULTIPLIER_X


def _print_buffer(_buffer:List[Word], blog_count: int):
    if len(_buffer) == 0:
        return blog_count
    print(colors[blog_count % len(colors)])
    print(f"; --- CÜMLE {blog_count + 1} ---")
    start_time = calc_time_period(_buffer[0].start_ms)
    end_time = calc_time_period(_buffer[-1].start_ms + _buffer[-1].duration)

    char_per_line = 0
    split_rules = []
    for i, word in enumerate(_buffer):
        char_per_line += len(word.key)
        if char_per_line > MAX_CHAR_PER_LINE:
            char_per_line = 0
            split_rules.append(i)
    
    x = 100
    y = (SCREEN_Y - PADDING) - CHAR_PIXEL - (len(split_rules) * CHAR_PIXEL)
    
    for i, word in enumerate(_buffer):
        if i in split_rules:
            y += CHAR_PIXEL
            x = 100
        # 1. Kelimenin X ve Y koordinatını yerleştir
        # \pos(x, y) etiketi
        print(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,", end='')
        print(r"{\pos(%d, %d)}%s" % (x, y, word.key), end="\n")

        # 2. Kelimenin ekranda kaplayacağı tahmini genişliği hesapla
        word_width = calculate_approx_width(word.key)

        # 3. Sonraki kelimenin başlangıç noktasını güncelle:
        # Yeni X = Mevcut X + Kelimenin Genişliği + Kelimeler Arası Boşluk
        x = x + word_width + SPACE_WIDTH
    print()
    return blog_count + 1
    

def parse_with_ms(word_list: List[Word], parse_ms: int, blog_count: int) -> int:
    _buffer: List[Word] = []
    if len(word_list) < pass_parse_ms_count:
        return _print_buffer(word_list, blog_count)
    for i in range(len(word_list) - 1):
        cWord = word_list[i]
        nWord = word_list[i + 1]
        _buffer.append(cWord)
        if nWord.start_ms - (cWord.start_ms + len(cWord.key) * char_time) > parse_ms:
            blog_count = _print_buffer(_buffer, blog_count)
            _buffer.clear()
    _buffer.append(word_list[-1])
    return _print_buffer(_buffer, blog_count)

        
def parse_with_senteces():
    sentences_end = ['.', '!', '?']
    sentences: List[Word] = []
    for i in range(len(word_list)-1):
        cWord = word_list[i]
        nWord = word_list[i+1]
        if cWord.key[-1] in sentences_end and nWord.key[0].isupper():
            sentences.append(cWord)
            sentences_list.append(copy(sentences))
            sentences.clear()
        else:
            sentences.append(cWord)
    sentences.append(word_list[-1])
    sentences_list.append(copy(sentences))
    
def print_sentences_list():
    c = 0
    for i in range(len(sentences_list)):
        c += 1
        sentences = sentences_list[i]
        c += parse_with_ms(sentences, stop_time, i)

def print_info():
    print(
"""
[Script Info]
; Bu betiğin hangi çözünürlüğe göre yazıldığını belirtir.
; pos(x,y) koordinatları bu çözünürlüğe göredir.
PlayResX: {0}
PlayResY: {1}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
; pos etiketinin sol-üst köşeyi baz alması için Alignment = 7 olmalı.
Style: Default,DejaVu Sans Mono,{2},&H000FFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,3,2,1,7,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text

""".format(SCREEN_X, SCREEN_Y, CHAR_PIXEL)
    )
    
        
def main(subtitle_name):
    subtitle_name = download_subtitle(subtitle_name)
    if subtitle_name is None:
        return
    print_info()
    en = load_subtitle(subtitle_name)
    process_events( en["events"])
    calc_duration()
    parse_with_senteces()
    print_sentences_list()

    
    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: python3 cut_analysis.py video_url")
        exit(-1)
    subtitle_name = sys.argv[1]
    main(subtitle_name)
