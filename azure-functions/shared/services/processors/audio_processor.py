import os
import re
import time
from typing import List

import requests

from shared.config.settings import (
    AZURE_WHISPER_ENDPOINT,
    AZURE_WHISPER_API_KEY,
    LLM_MAX_INPUT_TOKENS,
)
from shared.utils.logger import get_logger

logger = get_logger(__name__)

CHARS_PER_TOKEN = 4
SUPPORTED_AUDIO_FORMATS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".flac"}


class AudioProcessor:
    """
    Processes audio files using Azure OpenAI Whisper API.
    """

    def __init__(self):
        self.endpoint = AZURE_WHISPER_ENDPOINT
        self.api_key = AZURE_WHISPER_API_KEY
        logger.info(f"[AudioProcessor] Initialized")

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def process(self, file_path: str) -> List[dict]:
        logger.info(f"[AudioProcessor] Processing audio file...")
        start_time = time.time()

        if not self.is_configured():
            logger.error("[AudioProcessor] Whisper not configured")
            return [{
                "page_number": 1,
                "content_type": "text",
                "text_content": "[Audio file - Whisper not configured]",
                "char_count": 40,
                "estimated_tokens": 10
            }]

        transcript = self._transcribe_audio(file_path)

        if not transcript:
            return [{
                "page_number": 1,
                "content_type": "text",
                "text_content": "[Audio file - transcription failed or empty]",
                "char_count": 45,
                "estimated_tokens": 12
            }]

        sections = self._split_into_sections(transcript)

        elapsed = time.time() - start_time
        logger.info(f"[AudioProcessor] Done in {elapsed:.2f}s - {len(sections)} sections")

        return sections

    def _transcribe_audio(self, file_path: str) -> str:
        logger.info(f"[AudioProcessor] Transcribing audio: {file_path}")

        url = self.endpoint
        headers = {"api-key": self.api_key}

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        logger.info(f"[AudioProcessor] File size: {file_size:.2f} MB")

        try:
            with open(file_path, "rb") as audio_file:
                files = {
                    "file": (os.path.basename(file_path), audio_file, "audio/mpeg"),
                }
                data = {
                    "response_format": "verbose_json",
                    "language": "en",
                }

                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=300
                )

            if response.status_code != 200:
                logger.error(f"[AudioProcessor] Whisper API error: {response.status_code}")
                return ""

            result = response.json()
            transcript = result.get("text", "")
            duration = result.get("duration", 0)

            logger.info(f"[AudioProcessor] Transcription successful, duration: {duration:.1f}s")
            return transcript

        except Exception as e:
            logger.error(f"[AudioProcessor] Transcription error: {e}")
            return ""

    def _split_into_sections(self, transcript: str) -> List[dict]:
        sections = []
        section_num = 1

        safe_token_limit = LLM_MAX_INPUT_TOKENS - 2000
        safe_char_limit = safe_token_limit * CHARS_PER_TOKEN

        sentences = re.split(r'(?<=[.!?])\s+', transcript)

        current_content = []
        current_chars = 0

        def flush_section():
            nonlocal current_content, current_chars, section_num
            if current_content:
                text = " ".join(current_content)
                sections.append({
                    "page_number": section_num,
                    "content_type": "text",
                    "text_content": f"[AUDIO TRANSCRIPT - Section {section_num}]\n\n{text}",
                    "char_count": len(text),
                    "estimated_tokens": len(text) // CHARS_PER_TOKEN
                })
                section_num += 1
                current_content = []
                current_chars = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_chars = len(sentence)

            if current_chars + sentence_chars > safe_char_limit:
                flush_section()

            current_content.append(sentence)
            current_chars += sentence_chars + 1

        flush_section()

        if not sections:
            sections.append({
                "page_number": 1,
                "content_type": "text",
                "text_content": "[Empty audio transcript]",
                "char_count": 24,
                "estimated_tokens": 6
            })

        return sections
