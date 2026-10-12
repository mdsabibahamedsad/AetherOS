# AetherOS Reality Architecture

## Overview

The Reality Architecture unifies perception, reasoning, and action across digital and physical environments through a unified substrate.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UniversalRealityInterface                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Input        │  │  Fusion &    │  │  Output      │  │   Trust      │   │
│  │ Pipelines    │──▶│  Intent      │──▶│  Pipelines   │──▶│  Fabric      │   │
│  │              │  │  Resolver    │  │              │  │  (M55)       │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│         ▲                                                    │              │
│         │                                                    ▼              │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    Spatial Memory & World Model                     │  │
│  │  SpatialWorldModel │ Landmarks │ Routes │ Timeline │ Memory Engine  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    Hardware Adapters / Physical Layer               │  │
│  │  Cameras │ Microphones │ XR Headsets │ Robots │ Sensors │ Actuators │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Data Flow

```
Raw Sensors → Perception → Fusion → Grounding → Understanding
    ↓              ↓           ↓          ↓            ↓
World Model ← Intent Resolution ← Policy Check ← Capability Tokens
    ↓              ↓              ↓              ↓
Action ← Verification ← Execution ← Authorization ← Planning
```

## Key Abstractions

### Sensor Pipeline
- Abstract base class for all sensors
- Handles permission checks, availability, health
- Returns canonical MultimodalEvent objects

### Fusion Engine
- Early/late/hybrid fusion strategies
- Modality-weighted evidence aggregation
- Ambiguity scoring and clarification triggering

### Trust Fabric Integration
- Every action passes through ActionFirewall
- Capability tokens issued with Ed25519 signatures
- Revocation propagation through authority graph

### Spatial Memory
- Persistent entities with TTL and provenance
- Landmarks, routes, surveys
- Temporal fusion via MultimodalTimeline

## Data Flow Guarantees

1. **No fake sensors** - Unavailable = UNAVAILABLE, never fabricated
2. **Explicit modes** - Every event tagged SIMULATION/REPLAY/LIVE_HARDWARE
3. **Provenance chain** - Every fact traces to source sensor/model/pipeline
3. **Fail-closed** - Trust Fabric unavailable = deny high-risk
4. **Provenance chain** - Every fact traces to sensor/model/processing
4. **Reality check** - Prediction vs observation after every action