# OCR (Optical Character Recognition)

## Overview

AetherOS OCR provides text extraction from images, screenshots, and documents using multiple engines with language detection and image preprocessing.

## Supported Providers

| Provider | Type | Best For |
|----------|------|----------|
| Tesseract | Local | Offline OCR, common languages |
| Windows OCR | Local | Native Windows, system integration |
| Azure Vision | Cloud | Printed text, handwriting |
| Google Cloud Vision | Cloud | Diverse documents, layouts |
| AWS Textract | Cloud | Forms, tables, structured docs |
| Vision LLM | Cloud/API | Complex layouts, contextual extraction |

## Features

- Multi-language support (30+ languages)
- Auto-detect language
- Image enhancement (denoising, contrast)
- Deskew/straighten
- Page segmentation modes (PSM)
- Confidence scoring
- Block-level bounding boxes
- PDF text extraction

## Languages

| Code | Language | Code | Language |
|------|----------|------|----------|
| eng | English | fra | French |
| deu | German | spa | Spanish |
| ita | Italian | por | Portuguese |
| nld | Dutch | rus | Russian |
| jpn | Japanese | chi_sim | Chinese (Simplified) |
| chi_tra | Chinese (Traditional) | kor | Korean |
| ara | Arabic | hin | Hindi |
| tha | Thai | vie | Vietnamese |
| tur | Turkish | pol | Polish |
| ukr | Ukrainian | ell | Greek |
| heb | Hebrew | swe | Swedish |
| nor | Norwegian | dan | Danish |
| fin | Finnish | ces | Czech |
| hun | Hungarian | ron | Romanian |
| cat | Catalan | ind | Indonesian |
| msa | Malay | | |

## Store: `store/ocr-store.ts`

Manages:
- Provider selection
- Language configuration
- Processing status
- OCR results with confidence scores
- Image preprocessing settings
- PSM mode configuration

## Integration

OCR is integrated with:
- Screen understanding (auto-OCR on captures)
- File understanding (PDF/Office text extraction)
- Document preview
- Automation workflows (OCR action node)
- Smart workspace (image analysis)
