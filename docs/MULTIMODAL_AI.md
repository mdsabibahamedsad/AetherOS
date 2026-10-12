# Multimodal AI

## Overview

AetherOS Multimodal AI enables processing and understanding of text, images, audio, video, documents, screenshots, clipboard content, and camera input — all through a unified interface with automatic provider/ model routing.

## Supported Input Types

| Type | Input Methods | Processing |
|------|--------------|------------|
| Text | Keyboard, clipboard, drag & drop | Direct LLM |
| Images | Upload, drag & drop, clipboard, camera, screenshot | Vision models |
| Audio | Upload, microphone | Speech-to-text + analysis |
| Video | Upload, screen capture | Frame extraction + vision |
| PDF | Upload, drag & drop | OCR / text extraction / vision |
| Office Docs | Upload (.docx, .xlsx, .pptx) | Text conversion / OCR / vision |
| Screenshots | Screen capture hotkey | OCR + vision analysis |
| Clipboard | Auto-detect images/text | Content analysis |

## Architecture

```
┌─────────────────────────────┐
│   Multimodal Input Handler   │
│  ┌──────┐┌──────┐┌──────┐  │
│  │Image ││Audio ││Video │  │
│  │      ││      ││      │  │
│  └──────┘└──────┘└──────┘  │
│  ┌──────┐┌──────┐┌──────┐  │
│  │PDF   ││Office││Screen│  │
│  └──────┘└──────┘└──────┘  │
└──────────┬──────────────────┘
           │
┌──────────▼──────────────────┐
│   Model Routing Engine       │
│   ┌──────────────────────┐  │
│   │ Input Type Detection  │  │
│   │ Capability Matching   │  │
│   │ Provider Selection    │  │
│   │ Auto / Manual Route   │  │
│   └──────────────────────┘  │
└──────────┬──────────────────┘
           │
┌──────────▼──────────────────┐
│   AI Provider Backends      │
│   (OpenAI, Anthropic,       │
│    Google, OpenRouter, ...) │
└─────────────────────────────┘
```

## Capabilities

### Image Understanding
- Describe image contents
- Extract text (OCR)
- Analyze charts and diagrams
- Recognize objects and scenes
- Identify text in images

### Document Understanding
- PDF text extraction and analysis
- Word/Excel/PowerPoint processing
- Markdown rendering and conversion
- CSV/JSON/XML parsing

### Screen Understanding
- Full screen capture
- Window-specific capture
- Region selection
- Browser tab capture
- OCR on captured content
- AI-powered content analysis

### Camera & Microphone
- Live camera preview and capture
- Microphone audio input
- Real-time transcription
- Media recording

## Store: `store/multimodal.ts`

Manages:
- Camera enumeration and streams
- Screen capture state and permissions
- Privacy indicators (mic/camera/screen active states)
- Processing status per modality
- Model routing configuration
- Provider/model selection

## Privacy & Security

- All multimodal features require explicit user consent
- Screen capture requires display media permission
- Camera requires getUserMedia permission
- Microphone requires audio input permission
- Processing mode configurable: local / hybrid / cloud
- Privacy indicators show active recording state
- Consent timeout for automatic permission expiry
