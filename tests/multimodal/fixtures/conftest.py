"""Multimodal Test Fixtures (Phase 93).

Provides safe, synthetic test media for multimodal testing.
NO private user media is used — all fixtures are generated programmatically.
"""

from __future__ import annotations

import base64
import os
import struct
import tempfile
import wave
from pathlib import Path
from typing import BinaryIO, List, Optional

import pytest

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


# =============================================================================
# Fixture Paths
# =============================================================================

FIXTURE_DIR = Path(__file__).parent
FIXTURE_DIR.mkdir(exist_ok=True)

# Subdirectories
IMAGES_DIR = FIXTURE_DIR / "images"
AUDIO_DIR = FIXTURE_DIR / "audio"
VIDEO_DIR = FIXTURE_DIR / "video"
DOCS_DIR = FIXTURE_DIR / "documents"
CHARTS_DIR = FIXTURE_DIR / "charts"
TABLES_DIR = FIXTURE_DIR / "tables"
DIAGRAMS_DIR = FIXTURE_DIR / "diagrams"
SCREENSHOTS_DIR = FIXTURE_DIR / "screenshots"

for d in [IMAGES_DIR, AUDIO_DIR, VIDEO_DIR, DOCS_DIR, CHARTS_DIR, TABLES_DIR, DIAGRAMS_DIR, SCREENSHOTS_DIR]:
    d.mkdir(exist_ok=True)


# =============================================================================
# Image Fixtures
# =============================================================================

def create_test_image(
    path: Path,
    size: tuple = (100, 100),
    color: tuple = (255, 0, 0),
    format: str = "PNG",
    text: Optional[str] = None,
) -> Path:
    """Create a simple test image."""
    if not HAS_PIL:
        pytest.skip("Pillow not available")
    
    img = Image.new("RGB", size, color)
    if text:
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((10, 10), text, fill=(255, 255, 255), font=font)
    
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format=format)
    return path


def create_test_chart_image(path: Path, chart_type: str = "bar") -> Path:
    """Create a simple chart image."""
    if not HAS_PIL:
        pytest.skip("Pillow not available")
    
    img = Image.new("RGB", (400, 300), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    if chart_type == "bar":
        # Simple bar chart
        bars = [(50, 200, 80, 250), (150, 150, 180, 250), (250, 100, 280, 250), (350, 220, 380, 250)]
        for x1, y1, x2, y2 in bars:
            draw.rectangle([x1, y1, x2, y2], fill=(0, 100, 200), outline=(0, 50, 150))
        draw.text((50, 260), "Sample Bar Chart", fill=(0, 0, 0))
    elif chart_type == "line":
        # Simple line chart
        points = [(50, 200), (120, 180), (190, 120), (260, 160), (330, 80)]
        for i in range(len(points) - 1):
            draw.line([points[i], points[i+1]], fill=(200, 0, 100), width=3)
        draw.text((50, 260), "Sample Line Chart", fill=(0, 0, 0))
    elif chart_type == "pie":
        # Simple pie chart
        draw.pieslice([100, 50, 300, 250], 0, 90, fill=(200, 50, 50))
        draw.pieslice([100, 50, 300, 250], 90, 210, fill=(50, 200, 50))
        draw.pieslice([100, 50, 300, 250], 210, 360, fill=(50, 50, 200))
        draw.text((150, 260), "Sample Pie Chart", fill=(0, 0, 0))
    
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")
    return path


def create_test_diagram_image(path: Path, diagram_type: str = "flowchart") -> Path:
    """Create a simple diagram image."""
    if not HAS_PIL:
        pytest.skip("Pillow not available")
    
    img = Image.new("RGB", (400, 300), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    if diagram_type == "flowchart":
        # Simple flowchart
        boxes = [(50, 50, 150, 100), (200, 50, 300, 100), (125, 150, 225, 200)]
        for x1, y1, x2, y2 in boxes:
            draw.rectangle([x1, y1, x2, y2], fill=(200, 230, 255), outline=(50, 100, 200), width=2)
        draw.line([(150, 75), (200, 75)], fill=(50, 100, 200), width=2)
        draw.line([(250, 75), (175, 150)], fill=(50, 100, 200), width=2)
        draw.line([(50, 75), (175, 150)], fill=(50, 100, 200), width=2)
        draw.text((70, 65), "Start", fill=(0, 0, 0))
        draw.text((220, 65), "Process", fill=(0, 0, 0))
        draw.text((145, 165), "Decision", fill=(0, 0, 0))
    elif diagram_type == "architecture":
        # Simple architecture diagram
        draw.rectangle([50, 200, 150, 250], fill=(200, 255, 200), outline=(50, 150, 50), width=2)
        draw.rectangle([175, 200, 275, 250], fill=(200, 255, 200), outline=(50, 150, 50), width=2)
        draw.rectangle([300, 200, 400, 250], fill=(200, 255, 200), outline=(50, 150, 50), width=2)
        draw.rectangle([100, 50, 350, 150], fill=(255, 255, 200), outline=(150, 150, 50), width=2)
        draw.text((90, 215), "Service A", fill=(0, 0, 0))
        draw.text((210, 215), "Service B", fill=(0, 0, 0))
        draw.text((330, 215), "Service C", fill=(0, 0, 0))
        draw.text((200, 85), "API Gateway", fill=(0, 0, 0))
    
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")
    return path


def create_test_table_image(path: Path) -> Path:
    """Create a table image."""
    if not HAS_PIL:
        pytest.skip("Pillow not available")
    
    img = Image.new("RGB", (400, 250), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw table grid
    rows, cols = 4, 3
    cell_w, cell_h = 120, 40
    start_x, start_y = 20, 20
    
    headers = ["Name", "Value", "Status"]
    data = [
        ["Item A", "100", "Active"],
        ["Item B", "200", "Pending"],
        ["Item C", "300", "Complete"],
    ]
    
    # Header row
    for col, header in enumerate(headers):
        x1 = start_x + col * cell_w
        y1 = start_y
        x2 = x1 + cell_w
        y2 = y1 + cell_h
        draw.rectangle([x1, y1, x2, y2], fill=(50, 100, 200), outline=(0, 0, 0))
        draw.text((x1 + 5, y1 + 10), header, fill=(255, 255, 255))
    
    # Data rows
    for row_idx, row in enumerate(data):
        for col_idx, cell in enumerate(row):
            x1 = start_x + col_idx * cell_w
            y1 = start_y + (row_idx + 1) * cell_h
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            fill = (240, 240, 255) if row_idx % 2 == 0 else (255, 255, 255)
            draw.rectangle([x1, y1, x2, y2], fill=fill, outline=(150, 150, 150))
            draw.text((x1 + 5, y1 + 10), str(cell), fill=(0, 0, 0))
    
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")
    return path


def create_test_screenshot_image(path: Path) -> Path:
    """Create a mock screenshot with UI elements."""
    if not HAS_PIL:
        pytest.skip("Pillow not available")
    
    img = Image.new("RGB", (800, 600), (30, 30, 40))
    draw = ImageDraw.Draw(img)
    
    # Window bar
    draw.rectangle([0, 0, 800, 30], fill=(50, 50, 60), outline=(100, 100, 110))
    draw.text((10, 5), "terminal - bash", fill=(200, 200, 200))
    
    # Terminal content
    draw.text((20, 50), "$ python test.py", fill=(100, 255, 100))
    draw.text((20, 80), "Running tests...", fill=(200, 200, 200))
    draw.text((20, 110), "✓ test_passed", fill=(100, 255, 100))
    draw.text((20, 140), "✓ test_passed", fill=(100, 255, 100))
    draw.text((20, 170), "✗ test_failed", fill=(255, 100, 100))
    draw.text((20, 200), "AssertionError: expected 2, got 3", fill=(255, 200, 100))
    
    # Button-like elements
    draw.rectangle([600, 50, 700, 90], fill=(70, 130, 180), outline=(100, 150, 200))
    draw.text((615, 62), "Run Tests", fill=(255, 255, 255))
    draw.rectangle([600, 110, 700, 150], fill=(180, 70, 70), outline=(200, 100, 100))
    draw.text((615, 122), "Stop", fill=(255, 255, 255))
    
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")
    return path


# =============================================================================
# Audio Fixtures
# =============================================================================

def create_silence_wav(path: Path, duration: float = 1.0, sample_rate: int = 16000) -> Path:
    """Create a silent WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    num_samples = int(duration * sample_rate)
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        wav.writeframes(b'\x00\x00' * num_samples)
    return path


def create_tone_wav(path: Path, frequency: float = 440.0, duration: float = 1.0, sample_rate: int = 16000) -> Path:
    """Create a sine wave tone WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    num_samples = int(duration * sample_rate)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(32767 * 0.5 * __import__('math').sin(2 * __import__('math').pi * frequency * t))
        samples.append(struct.pack('<h', value))
    
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b''.join(samples))
    return path


def create_speech_like_wav(path: Path, duration: float = 3.0, sample_rate: int = 16000) -> Path:
    """Create a WAV that resembles speech (formant-like)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    import math
    import random
    
    num_samples = int(duration * sample_rate)
    samples = []
    
    # Simulate formants (F1=700, F2=1200, F3=2500 Hz)
    formants = [700, 1200, 2500]
    bandwidths = [100, 150, 200]
    
    for i in range(num_samples):
        t = i / sample_rate
        # Modulate amplitude to simulate speech envelopes
        envelope = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(2 * math.pi * 3 * t)) * (0.5 + 0.5 * math.sin(2 * math.pi * 7 * t))
        
        value = 0
        for f, bw in zip(formants, bandwidths):
            value += math.sin(2 * math.pi * f * t) * math.exp(-bw * t * 0.001)
        
        value = value / len(formants) * envelope * 10000
        value = max(-32767, min(32767, int(value)))
        samples.append(struct.pack('<h', value))
    
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b''.join(samples))
    return path


# =============================================================================
# Video Fixtures
# =============================================================================

def create_test_video_mp4(path: Path, duration: float = 2.0, fps: int = 10, size: tuple = (320, 240)) -> Path:
    """Create a simple test video using ffmpeg if available, otherwise create frame sequence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        import subprocess
        # Try to use ffmpeg to create a real video
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi',
            '-i', f'testsrc=duration={duration}:size={size[0]}x{size[1]}:rate={fps}',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-t', str(duration),
            str(path)
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0 and path.exists():
            return path
    except (ImportError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Fallback: create a simple frame sequence as a fake video
    # This is a minimal MP4 container with minimal data
    # For testing purposes, we'll create a very simple file
    with open(path, 'wb') as f:
        # Minimal MP4 header (ftyp box)
        f.write(b'\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41')
        # Moov box placeholder
        f.write(b'\x00\x00\x00\x08moov')
    
    return path


def create_test_video_frames_dir(dir_path: Path, num_frames: int = 10, size: tuple = (320, 240)) -> List[Path]:
    """Create a directory of test video frames."""
    if not HAS_PIL:
        pytest.skip("Pillow not available")
    
    dir_path.mkdir(parents=True, exist_ok=True)
    frames = []
    
    for i in range(num_frames):
        img = Image.new("RGB", size, (i * 25 % 256, i * 15 % 256, i * 35 % 256))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), f"Frame {i+1}/{num_frames}", fill=(255, 255, 255))
        frame_path = dir_path / f"frame_{i:04d}.png"
        img.save(frame_path, format="PNG")
        frames.append(frame_path)
    
    return frames


# =============================================================================
# Document Fixtures
# =============================================================================

def create_test_pdf(path: Path, content: str = "Test PDF Document\n\nThis is a test document.\n\nPage 2 content here.") -> Path:
    """Create a simple test PDF."""
    if HAS_FITZ:
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), content, fontsize=12)
        doc.save(path)
        doc.close()
        return path
    else:
        # Create a minimal PDF manually
        path.parent.mkdir(parents=True, exist_ok=True)
        pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 72 720 Td (Test PDF) Tj ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000218 00000 n 
0000000300 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
380
%%EOF"""
        path.write_bytes(pdf_content.encode('latin-1'))
        return path


def create_test_docx(path: Path, content: str = "Test DOCX Document\n\nThis is a test document.") -> Path:
    """Create a simple test DOCX."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        from docx import Document
        doc = Document()
        for para in content.split('\n\n'):
            doc.add_paragraph(para)
        doc.save(path)
        return path
    except ImportError:
        # Create minimal DOCX (ZIP with XML)
        import zipfile
        with zipfile.ZipFile(path, 'w') as zf:
            zf.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')
            zf.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')
            zf.writestr('word/document.xml', f'''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:r><w:t>{content.replace(chr(10), '</w:t></w:r></w:p><w:p><w:r><w:t>')}</w:t></w:r></w:p>
</w:body>
</w:document>''')
        return path


def create_test_txt(path: Path, content: str = "Test text document\n\nLine 1\nLine 2\nLine 3") -> Path:
    """Create a simple test text file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def create_test_md(path: Path, content: str = "# Test Markdown\n\n## Section 1\n\nContent here.\n\n## Section 2\n\n- Item 1\n- Item 2") -> Path:
    """Create a simple test Markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def create_test_csv(path: Path) -> Path:
    """Create a simple test CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "Name,Value,Status\nItem A,100,Active\nItem B,200,Pending\nItem C,300,Complete\n"
    path.write_text(content, encoding='utf-8')
    return path


def create_test_json(path: Path) -> Path:
    """Create a simple test JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    import json
    data = {
        "name": "Test Object",
        "version": "1.0",
        "items": [
            {"id": 1, "name": "Item A", "active": True},
            {"id": 2, "name": "Item B", "active": False},
        ],
        "metadata": {
            "created": "2024-01-01",
            "tags": ["test", "fixture"]
        }
    }
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return path


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    """Return the fixture directory."""
    return FIXTURE_DIR


@pytest.fixture(scope="session")
def test_image_simple(fixture_dir) -> Path:
    """Simple test image (red square)."""
    return create_test_image(fixture_dir / "images" / "simple_red.png", color=(255, 0, 0))


@pytest.fixture(scope="session")
def test_image_with_text(fixture_dir) -> Path:
    """Test image with text."""
    return create_test_image(fixture_dir / "images" / "with_text.png", text="Hello World")


@pytest.fixture(scope="session")
def test_screenshot(fixture_dir) -> Path:
    """Mock terminal screenshot."""
    return create_test_screenshot_image(fixture_dir / "screenshots" / "terminal.png")


@pytest.fixture(scope="session")
def test_chart_bar(fixture_dir) -> Path:
    """Bar chart image."""
    return create_test_chart_image(fixture_dir / "charts" / "bar_chart.png", "bar")


@pytest.fixture(scope="session")
def test_chart_line(fixture_dir) -> Path:
    """Line chart image."""
    return create_test_chart_image(fixture_dir / "charts" / "line_chart.png", "line")


@pytest.fixture(scope="session")
def test_chart_pie(fixture_dir) -> Path:
    """Pie chart image."""
    return create_test_chart_image(fixture_dir / "charts" / "pie_chart.png", "pie")


@pytest.fixture(scope="session")
def test_diagram_flowchart(fixture_dir) -> Path:
    """Flowchart diagram."""
    return create_test_diagram_image(fixture_dir / "diagrams" / "flowchart.png", "flowchart")


@pytest.fixture(scope="session")
def test_diagram_architecture(fixture_dir) -> Path:
    """Architecture diagram."""
    return create_test_diagram_image(fixture_dir / "diagrams" / "architecture.png", "architecture")


@pytest.fixture(scope="session")
def test_table_image(fixture_dir) -> Path:
    """Table image."""
    return create_test_table_image(fixture_dir / "tables" / "table.png")


@pytest.fixture(scope="session")
def test_audio_silence(fixture_dir) -> Path:
    """Silent audio file."""
    return create_silence_wav(fixture_dir / "audio" / "silence.wav", duration=1.0)


@pytest.fixture(scope="session")
def test_audio_tone(fixture_dir) -> Path:
    """Tone audio file."""
    return create_tone_wav(fixture_dir / "audio" / "tone_440hz.wav", frequency=440.0, duration=1.0)


@pytest.fixture(scope="session")
def test_audio_speech_like(fixture_dir) -> Path:
    """Speech-like audio file."""
    return create_speech_like_wav(fixture_dir / "audio" / "speech_like.wav", duration=2.0)


@pytest.fixture(scope="session")
def test_video_short(fixture_dir) -> Path:
    """Short test video."""
    return create_test_video_mp4(fixture_dir / "video" / "short.mp4", duration=1.0)


@pytest.fixture(scope="session")
def test_video_frames(fixture_dir) -> List[Path]:
    """Video frames directory."""
    return create_test_video_frames_dir(fixture_dir / "video" / "frames", num_frames=5)


@pytest.fixture(scope="session")
def test_pdf_simple(fixture_dir) -> Path:
    """Simple PDF document."""
    return create_test_pdf(fixture_dir / "documents" / "simple.pdf")


@pytest.fixture(scope="session")
def test_docx_simple(fixture_dir) -> Path:
    """Simple DOCX document."""
    return create_test_docx(fixture_dir / "documents" / "simple.docx")


@pytest.fixture(scope="session")
def test_txt_simple(fixture_dir) -> Path:
    """Simple text file."""
    return create_test_txt(fixture_dir / "documents" / "simple.txt")


@pytest.fixture(scope="session")
def test_md_simple(fixture_dir) -> Path:
    """Simple Markdown file."""
    return create_test_md(fixture_dir / "documents" / "simple.md")


@pytest.fixture(scope="session")
def test_csv_simple(fixture_dir) -> Path:
    """Simple CSV file."""
    return create_test_csv(fixture_dir / "documents" / "simple.csv")


@pytest.fixture(scope="session")
def test_json_simple(fixture_dir) -> Path:
    """Simple JSON file."""
    return create_test_json(fixture_dir / "documents" / "simple.json")


# =============================================================================
# Base64 Encoded Fixtures (for API testing)
# =============================================================================

@pytest.fixture(scope="session")
def test_image_base64(test_image_simple) -> str:
    """Base64 encoded test image."""
    with open(test_image_simple, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')


@pytest.fixture(scope="session")
def test_audio_base64(test_audio_tone) -> str:
    """Base64 encoded test audio."""
    with open(test_audio_tone, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')


@pytest.fixture(scope="session")
def test_pdf_base64(test_pdf_simple) -> str:
    """Base64 encoded test PDF."""
    with open(test_pdf_simple, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')


# =============================================================================
# MediaObject Fixtures
# =============================================================================

@pytest.fixture
def media_image(test_image_simple) -> "MediaObject":
    """MediaObject for test image."""
    from agent.multimodal.media_abstraction import create_image_media
    return create_image_media(str(test_image_simple))


@pytest.fixture
def media_audio(test_audio_tone) -> "MediaObject":
    """MediaObject for test audio."""
    from agent.multimodal.media_abstraction import create_audio_media
    return create_audio_media(str(test_audio_tone))


@pytest.fixture
def media_video(test_video_short) -> "MediaObject":
    """MediaObject for test video."""
    from agent.multimodal.media_abstraction import create_video_media
    return create_video_media(str(test_video_short))


@pytest.fixture
def media_document(test_pdf_simple) -> "MediaObject":
    """MediaObject for test document."""
    from agent.multimodal.media_abstraction import create_document_media
    return create_document_media(str(test_pdf_simple))


@pytest.fixture
def media_text() -> "MediaObject":
    """MediaObject for text."""
    from agent.multimodal.media_abstraction import create_text_media
    return create_text_media("This is test text content for multimodal processing.")


@pytest.fixture
def media_structured() -> "MediaObject":
    """MediaObject for structured data."""
    from agent.multimodal.media_abstraction import create_structured_data_media
    return create_structured_data_media({"key": "value", "numbers": [1, 2, 3]}, format="json")


# =============================================================================
# Cleanup
# =============================================================================

def pytest_sessionfinish(session, exitstatus):
    """Clean up any temporary files after test session."""
    pass  # Fixtures are in a permanent directory, no cleanup needed