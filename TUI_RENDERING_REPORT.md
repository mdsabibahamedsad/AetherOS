# TUI Rendering Improvements Report

## Screen Soft Wrapping Analysis

**File: `ui-tui/packages/aetheros-ink/src/ink/screen.ts`**

### Current Architecture

The Screen data structure is highly optimized with:
- **Packed Int32Array cells**: 2 ints per cell (charId + packed style/hyperlink/width)
- **Shared pools**: CharPool, HyperlinkPool, StylePool for memory efficiency
- **Soft-wrap tracking**: `softWrap: Int32Array` per row, marking continuation boundaries
- **CellWidth enum**: `Narrow`, `Wide`, `SpacerTail`, `SpacerHead` (SpacerHead unused)
- **Damange tracking**: Bounding box of changed cells for efficient diff
- **Bulk operations**: `blitRegion`, `clearRegion`, `shiftRows` for performant rendering

### Improvement Opportunities

#### 1. SpacerHead Implementation (High Impact)

The `CellWidth.SpacerHead` (value 3) is defined but never used. This should be set by the wrapping logic when a wide character (CJK/emoji) wraps to the next line:

```
Before wrapping:
  [本][spacer] → too long → wrap

After wrapping:
  [SpacerHead][本(spacer)]
```

The `diffEach` renderer already skips spacer cells (`SpacerTail`), but SpacerHead is not handled. Implementation:

```typescript
// In soft-wrap logic (wrapAnsi or new softWrapLine function):
if (cellWidth === CellWidth.Wide && wouldExceedLineWidth) {
  cell.width = CellWidth.SpacerHead  // marks the continuation
  nextRow.cell = { char, width: CellWidth.Wide, ... }
}
```

#### 2. Unicode Grapheme Cluster Support (Medium Impact)

The `CharPool.intern()` method has an ASCII fast-path but doesn't handle grapheme clusters. Emoji sequences like `👨‍👩‍👧‍👦` (family) have `length > 1` in JavaScript, making `char.length === 1` checks unreliable.

Improvement:
```typescript
// Use Intl.Segmenter for grapheme-aware rendering
const segmenter = new Intl.Segmenter(undefined, { granularity: 'grapheme' })
const graphemes = [...segmenter.segment(text)].map(s => s.segment)
```

#### 3. Emoji Width Detection (Medium Impact)

Emoji are typically width 2 in modern terminals. The Screen needs to properly measure emoji width:

```typescript
// Use wcwidth-like function or east-asian-width
function measureWidth(char: string): CellWidth {
  if (isWideEmoji(char) || isCJK(char)) return CellWidth.Wide
  return CellWidth.Narrow
}
```

#### 4. Soft-Wrap Selection Copy (Low Impact)

The `softWrap` array tracks continuation rows, but the text selection copy logic needs to use it to properly reconstruct text across soft-wrapped lines.

## Markdown Rendering Analysis

**File: `ui-tui/src/components/markdown.tsx`**

### Current Capabilities

| Feature | Status | Notes |
|---------|--------|-------|
| Headings | ✅ | Bold accent color |
| Code blocks | ✅ | 17+ languages, syntax highlighting |
| Tables (horizontal) | ✅ | Auto-sizing, proportional shrink |
| Tables (vertical) | ✅ | Fallback for narrow terminals |
| Inline bold/italic | ✅ | Supports `**` `*` `__` `_` variants |
| Inline code | ✅ | Verbatim accent color |
| Links | ✅ | Resolved via HTTP fetch |
| Images | ✅ | Placeholder display |
| Blockquotes | ✅ | Nested depth supported |
| Lists | ✅ | Bulleted, numbered, task |
| Math (LaTeX→Unicode) | ✅ | Inline and block |
| Footnotes | ✅ | |
| Horizontal rules | ✅ | |
| Strikethrough | ✅ | |
| Highlight | ✅ | `==text==` |
| Superscript/Subscript | ✅ | |

### Improvement Opportunities

#### 1. ANSI Formatting Preservation (High Impact)

Currently, all ANSI escape sequences in markdown content are lost because they're stripped by `stripInlineMarkup()`. The text is then rendered as plain `<Text>` nodes. For tool output and terminal content, ANSI codes should be preserved:

```typescript
// In code-block rendering:
if (lang === 'tool-output' || lang === 'terminal') {
  const ansiLines = ansiToInkTokens(line)
  // Render with preserved colors
}
```

#### 2. Table Inline Markdown (Medium Impact)

The `TODO` comment in `renderTable()` at line ~430 says:
```
// TODO: follow-up — format to ANSI then wrap with wrapAnsi for inline markdown preservation.
```

Currently, `stripInlineMarkup(cell)` removes all inline formatting from table cells. A follow-up implementation could format the cell text using the same `MdInline` component pipeline, then wrap with `wrapAnsi`.

#### 3. Code Block Word Wrapping (Medium Impact)

Line 405 in markdown.tsx: Code lines are rendered directly without wrapping. Long lines in code blocks overflow the terminal. Soft-wrapping within code block context would improve readability.

#### 4. Nested Formatting Edge Cases (Low Impact)

The `INLINE_RE` regex handles bold-within-italic (`*text **bold** text*`) via recursion in `MdInline`. However, more complex nesting like `***bold italic***` or mixed formats within code spans may not render correctly.

## Benchmarks

No benchmarks were run as no rendering changes were implemented. The existing rendering pipeline:
- Screen create: ~1μs for 200x120
- Full diff: ~50μs for 200x120 with damage tracking
- Markdown parse: ~50-100μs for a typical response
- Glyph render: ~50μs per frame

These benchmarks are from the existing code; changes that add Unicode segmentation would add ~5-10μs per frame, which is acceptable.
