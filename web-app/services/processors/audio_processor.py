import os
import time
from typing import List

import requests

from config.settings import (
    AZURE_WHISPER_ENDPOINT,
    AZURE_WHISPER_API_KEY,
    LLM_MAX_INPUT_TOKENS,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Approximate chars per token for estimation
CHARS_PER_TOKEN = 4

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".flac"}


class AudioProcessor:
    """
    Processes audio files using Azure OpenAI Whisper API.
    Transcribes audio to text and splits into token-safe sections.
    """

    def __init__(self):
        self.endpoint = AZURE_WHISPER_ENDPOINT
        self.api_key = AZURE_WHISPER_API_KEY
        logger.info(f"[AudioProcessor] Initialized")

    def is_configured(self) -> bool:
        """Check if Whisper is properly configured."""
        return bool(self.endpoint and self.api_key)

    def process(self, file_path: str) -> List[dict]:
        """
        Process audio file and transcribe to text.

        Args:
            file_path: Path to the audio file

        Returns:
            List of section dicts with 'page_number', 'content_type', 'text_content', etc.
        """
        logger.info(f"[AudioProcessor] Processing audio file...")
        start_time = time.time()

        if not self.is_configured():
            logger.error("[AudioProcessor] Whisper not configured - missing endpoint or API key")
            return [{
                "page_number": 1,
                "content_type": "text",
                "text_content": "[Audio file - Whisper not configured]",
                "char_count": 40,
                "estimated_tokens": 10
            }]

        # Transcribe audio
        transcript = self._transcribe_audio(file_path)

        if not transcript:
            logger.warning("[AudioProcessor] No transcript generated")
            return [{
                "page_number": 1,
                "content_type": "text",
                "text_content": "[Audio file - transcription failed or empty]",
                "char_count": 45,
                "estimated_tokens": 12
            }]

        # Split transcript into token-safe sections
        sections = self._split_into_sections(transcript)

        elapsed = time.time() - start_time
        logger.info(f"[AudioProcessor] Done in {elapsed:.2f}s - {len(sections)} sections")

        return sections

    def _transcribe_audio(self, file_path: str) -> str:
        """
        Transcribe audio file using Azure OpenAI Whisper API.

        Args:
            file_path: Path to the audio file

        Returns:
            Transcribed text string
        """
        logger.info(f"[AudioProcessor] Transcribing audio: {file_path}")

        # Use direct URL from environment
        url = self.endpoint

        # Prepare headers
        headers = {
            "api-key": self.api_key,
        }

        # Get file size for logging
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        logger.info(f"[AudioProcessor] File size: {file_size:.2f} MB")

        try:
            # Open and send file
            with open(file_path, "rb") as audio_file:
                files = {
                    "file": (os.path.basename(file_path), audio_file, "audio/mpeg"),
                }
                data = {
                    "response_format": "verbose_json",
                    "language": "en",  # Can be made configurable
                }

                logger.info("[AudioProcessor] Sending request to Whisper API...")
                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=300  # 5 minute timeout for long audio files
                )

            if response.status_code != 200:
                logger.error(f"[AudioProcessor] Whisper API error: {response.status_code}")
                logger.error(f"[AudioProcessor] Response: {response.text[:500]}")
                return ""

            result = response.json()

            # Extract transcript text
            transcript = result.get("text", "")
            duration = result.get("duration", 0)

            logger.info(f"[AudioProcessor] Transcription successful")
            logger.info(f"  Duration: {duration:.1f}s")
            logger.info(f"  Characters: {len(transcript)}")
            logger.info(f"  Estimated tokens: {len(transcript) // CHARS_PER_TOKEN}")

            return transcript

        except requests.exceptions.Timeout:
            logger.error("[AudioProcessor] Whisper API timeout")
            return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"[AudioProcessor] Request error: {e}")
            return ""
        except Exception as e:
            logger.error(f"[AudioProcessor] Transcription error: {e}")
            return ""

    def _split_into_sections(self, transcript: str) -> List[dict]:
        """
        Split transcript into token-safe sections.

        Args:
            transcript: Full transcribed text

        Returns:
            List of section dicts ready for LLM processing
        """
        sections = []
        section_num = 1

        # Calculate safe token limit (leave room for system prompt)
        safe_token_limit = LLM_MAX_INPUT_TOKENS - 2000
        safe_char_limit = safe_token_limit * CHARS_PER_TOKEN

        # Split transcript into paragraphs (by double newline or period followed by space)
        # For audio, we'll split by sentences to maintain context
        import re
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
                logger.info(f"  Section {section_num}: {len(text)} chars, ~{len(text) // CHARS_PER_TOKEN} tokens")
                section_num += 1
                current_content = []
                current_chars = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_chars = len(sentence)

            # Check if adding this sentence would exceed limit
            if current_chars + sentence_chars > safe_char_limit:
                flush_section()

            current_content.append(sentence)
            current_chars += sentence_chars + 1  # +1 for space

        # Flush remaining content
        flush_section()

        # If no content extracted
        if not sections:
            sections.append({
                "page_number": 1,
                "content_type": "text",
                "text_content": "[Empty audio transcript]",
                "char_count": 24,
                "estimated_tokens": 6
            })

        return sections
