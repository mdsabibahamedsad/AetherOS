from __future__ import annotations

import re


class AutoCorrect:
    def __init__(self):
        self._punctuation_rules = [
            (r'\b(and)\b', r', and'),
            (r'\b(but)\b', r', but'),
            (r'\b(however)\b', r', however'),
            (r'\b(therefore)\b', r', therefore'),
            (r'\b(because)\b', r', because'),
        ]
        self._sentence_endings = re.compile(r'(?<=[.!?])\s+')
        self._new_sentence = re.compile(r'^[a-z]')

    def add_punctuation(self, text: str) -> str:
        text = text.strip()
        if not text:
            return text
        # Capitalize first letter
        text = text[0].upper() + text[1:] if text else text
        # Ensure sentence-ending punctuation
        if text and text[-1] not in ".!?":
            text += "."
        # Fix common dictation issues
        text = re.sub(r'\s+([,.:;!?])', r'\1', text)
        return text

    def correct_grammar(self, text: str) -> str:
        replacements = [
            (r'\bi\b', 'I'),
            (r'\bi\'m\b', "I'm"),
            (r'\bi\'ve\b', "I've"),
            (r'\bi\'ll\b', "I'll"),
            (r'\bid\b', "I'd"),
            (r'\bdont\b', "don't"),
            (r'\bdoesnt\b', "doesn't"),
            (r'\bwont\b', "won't"),
            (r'\bcant\b', "can't"),
            (r'\bcouldnt\b', "couldn't"),
            (r'\bwouldnt\b', "wouldn't"),
            (r'\bshouldnt\b', "shouldn't"),
            (r'\bim\b', "I'm"),
            (r'\bive\b', "I've"),
            (r'\btheres\b', "there's"),
            (r'\bits\b', "it's"),
            (r'\byoure\b', "you're"),
            (r'\btheyre\b', "they're"),
            (r'\bwelcome\b', "you're welcome"),
        ]
        result = text
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result
