from typing import Optional

from quickmt import Translator
import spacy
import json
import asyncio
import aiofiles
import string


nlp = spacy.load("en_core_web_trf")
dictionary = {}

async def read_file():
    global dictionary
    async with aiofiles.open('dictionary.txt', mode='r') as f:
        contents = await f.read()
        dictionary = json.loads(contents)

asyncio.run(read_file())

to_tr_type = {'noun': 'isim',
              "adjective": 'sifat',
              "adverb": 'zarf',
              "interjection": 'etkilesim',
              "abbreviation": "kisaltma",
              "expression": 'ifade',
              "verb": "fiil",
              "prefix": "on-ek",
              "exclamation": "unlem.",
              "suffix": "son-ek",
              "preposition": "edat",
              "other": "diger",
              "conjunction": "baglac",
              "pronoun": "zamir"
              }



def clear_word(word: str):
    word.lower()
    if word[-1] in string.punctuation:
        return word[:-1]
    return word

def translate_word(word: str) -> str:
    processed_word = nlp(word)
    processed_word = clear_word(processed_word.text)
    
    
    tr: Optional[dict] = dictionary.get(processed_word)
    if tr is None:
        return word

    tr_text = ''
    for key, val_list in tr.items():
        tr_text += to_tr_type.get(key) + ":\n"
        tr_text += ", ".join(val_list[:2])

        tr_text +="\n\n"
        
    
    return tr_text
