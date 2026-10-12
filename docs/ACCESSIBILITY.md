# Accessibility

## Overview

AetherOS provides comprehensive accessibility features for users with vision, hearing, and mobility needs.

## Vision

### Screen Reader
- Screen reader support for visually impaired users
- Navigate all UI elements with assistive technology
- ARIA labels on all interactive elements

### Display
- **High Contrast Mode**: Increased visual contrast for readability
- **Contrast Modes**: Normal, high contrast, dark, light
- **Font Size**: Small, normal, large, x-large options
- **Large Fonts**: Increased text size throughout
- **Custom Font Size**: Adjustable base font size (12-24px)
- **Reduce Motion**: Minimize animations and transitions
- **Reduce Transparency**: Decrease transparent UI elements
- **Focus Indicator**: Visible keyboard focus ring
- **Focus Indicator Width**: Adjustable focus ring thickness

## Hearing

### Captions
- Real-time captions for audio content
- Caption style options: default, large, high contrast
- Visual indicators for audio events

### Announcements
- Screen reader announcement volume control
- Audio feedback for UI interactions

## Mobility

### Keyboard Navigation
- Full keyboard navigation through all UI elements
- Tab order follows logical layout
- Keyboard shortcuts for common actions
- Focus trapping in modals and dialogs

### Voice Navigation
- Navigate the interface using voice commands
- Speech-to-text for text input
- Voice-controlled actions and commands

### Filter Keys
- **Sticky Keys**: One key at a time for modifier combinations
- **Slow Keys**: Delay before key press registers
- **Bounce Keys**: Ignore accidental repeated keystrokes
- **Toggle Keys**: Audio feedback for toggle keys

### Typing Feedback
- Off: No typing feedback
- Sound: Audio click on key press
- Voice: Spoken character feedback

## Implementation

Accessibility features are managed through the `store/accessibility-store.ts` store and can be configured in Settings > Accessibility.

All settings persist across sessions and are applied immediately.

## Compliance

AetherOS aims to comply with:
- WCAG 2.1 Level AA
- Section 508 of the Rehabilitation Act
- EN 301 549 (European accessibility standard)
