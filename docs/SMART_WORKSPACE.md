# Smart Workspace

## Overview

AetherOS Smart Workspace provides a visual environment for organizing thoughts, documents, tasks, and AI interactions through multiple interconnected tools.

## Components

### AI Canvas
- Interactive node-based canvas
- Supports text, image, code, link, note, file nodes
- Drag-and-drop positioning
- Node connections with quadratic bezier curves
- Zoom (scroll) and pan (middle-click / Shift+drag)
- Mini-map for navigation
- Context menu for node operations
- Snap-to-grid layout
- Auto-layout algorithm

### Mind Map
- Tree-structured node hierarchy
- Collapsible branches
- Editable node labels (double-click)
- Color-coded by depth level
- Add child nodes interactively
- Zoom controls

### Whiteboard
- Freehand drawing with pen strokes
- Shape drawing (future)
- Eraser tool
- Stroke undo
- Configurable stroke color and width
- Opacity control

### Scratchpad
- Free-form text editing
- Version history with snapshots
- Save/restore snapshots
- Quick notes and drafts

### Notes
- Rich text notes with tags
- Multiple view modes: grid, list, timeline
- Pin/unpin important notes
- Search and filter
- AI-powered categorization

### Knowledge Panel
- Browse and search knowledge base
- Quick access to saved information
- Integration with AI memory

### Task Panel
- View and manage tasks
- Quick task creation
- Task status tracking

### Bookmarks
- Save and organize URLs
- Tag-based categorization
- Quick access sidebar

### Pinned Chats
- Pin important conversations
- Quick resume from sidebar
- Persistent across sessions

## Store: `store/smart-workspace.ts`

Manages:
- Workspace items (canvas, scratchpad, notes, whiteboard, mindmap)
- Canvas nodes with positions, connections
- Mind map tree structure
- Whiteboard strokes
- Scratchpad content and history
- Bookmarks and pinned chats
- View preferences and search

## Store: `store/screen-understanding.ts`

Manages:
- Screen capture mode and status
- Capture history
- OCR and analysis settings
- Window enumeration
- Region selection
- Privacy controls

## Store: `store/file-understanding.ts`

Manages:
- File analysis results
- Document type detection
- Processing method selection
- Recent analyses history
- Size limits and auto-analysis settings
