# Voice Assistant

## Overview

AetherOS Voice Assistant provides always-available voice interaction with push-to-talk, voice activation, and always-on modes. It supports multiple speech-to-text and text-to-speech providers with hardware acceleration and noise suppression.

## Architecture

```
┌──────────────────────────────┐
│    Floating Assistant UI      │
│  ┌──────────┐ ┌────────────┐ │
│  │  PTT/Wake│ │Transcript  │ │
│  │  Trigger │ │Display     │ │
│  └────┬─────┘ └────────────┘ │
│       │                      │
│  ┌────▼─────────────────┐   │
│  │  Voice Assistant Store │   │
│  │  (activation, state,  │   │
│  │   devices, providers) │   │
│  └────┬─────────────────┘   │
└───────┼──────────────────────┘
        │
┌───────▼────────────────────────┐
│  Speech-to-Text (STT) Engines  │
│  ┌──────┬──────┬──────┬──────┐ │
│  │Whispe│Azure │Google│Deepgr│ │
│  │r     │      │      │am    │ │
│  └──────┴──────┴──────┴──────┘ │
└───────┬────────────────────────┘
        │
┌───────▼────────────────────────┐
│  Text-to-Speech (TTS) Engines  │
│  ┌──────┬──────┬──────┬──────┐ │
│  │Edge  │OpenAI│Eleven│Azure │ │
│  │      │      │Labs  │      │ │
│  └──────┴──────┴──────┴──────┘ │
└────────────────────────────────┘
```

## Activation Modes

| Mode | Description |
|------|-------------|
| Push-to-Talk | Hold a key while speaking |
| Voice Activation | Say wake word to activate |
| Always On | Continuous listening |
| Disabled | Voice assistant off |

## Features

- **Noise Suppression**: Standard, aggressive, or low filtering
- **Echo Cancellation**: Removes speaker echo from mic input
- **Auto Gain Control**: Automatically adjusts mic sensitivity
- **Silence Detection**: Auto-stops on silence with configurable threshold and timeout
- **Voice Activity Detection**: Detects when user is speaking
- **Microphone Selection**: Choose between available input devices
- **Speaker Selection**: Choose output device

## STT Providers

| Provider | Type | Features |
|----------|------|----------|
| OpenAI Whisper | Cloud | High accuracy, multiple models |
| Whisper.cpp | Local | Fast local inference |
| Faster-Whisper | Local | Optimized local inference |
| Azure Speech | Cloud | Microsoft STT |
| Google Speech | Cloud | Google STT |
| Deepgram | Cloud | Real-time STT |
| AssemblyAI | Cloud | Async STT |
| Custom | Any | Custom provider support |

## TTS Providers

| Provider | Type | Features |
|----------|------|----------|
| Edge (Windows Native) | Local | Windows built-in voices |
| OpenAI TTS | Cloud | Natural voices |
| Azure TTS | Cloud | Microsoft neural voices |
| Google TTS | Cloud | Google WaveNet voices |
| ElevenLabs | Cloud | Premium AI voices |
| Custom | Any | Custom provider support |

## UI Components

- **FloatingAssistant**: Draggable floating assistant window
- **VoiceSettingsPanel**: Full voice configuration panel
- **PrivacyIndicators**: Mic/camera/screen active indicators

## Store: `store/voice-assistant.ts`

Manages:
- Activation mode state
- Processing state (idle/listening/processing/speaking/error)
- Microphone/speaker device enumeration
- Noise suppression configuration
- STT/TTS provider selection
- Floating assistant position and size
- Volume level and latency monitoring

## Privacy

- All voice processing requires explicit microphone permission
- Processing mode selection: local, hybrid, or cloud
- Ask-before-upload for cloud processing
- Privacy indicators show when mic is active
- Offline mode available for local-only processing
