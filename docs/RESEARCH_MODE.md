# Research Mode

The Research Mode enables multi-source web research with automatic citation, contradiction detection, and report generation.

## Architecture

```
aetheros_automation/browser_automation/research_mode.py
```

The `ResearchMode` class manages research sessions, source analysis, finding extraction, and report generation.

## Features

### Research Sessions
- Start research with a query and optional source URLs
- Add sources incrementally during a session
- Track status (in_progress → completed)

### Source Analysis
- Automatic page navigation and content extraction
- Title and snippet capture
- Relevance scoring

### Finding Extraction
- Extract key facts from research sources
- Categorize findings (general, insights, safety, etc.)
- Confidence scoring for each finding

### Contradiction Detection
- Cross-source comparison using word overlap analysis
- Identifies discrepancies between sources
- Reports overlap percentage

### Report Generation
- Markdown-formatted research reports
- Categorized findings with source citations
- Contradiction warnings
- Source count and finding statistics

### Knowledge Hub Integration
- Save completed research reports to the Knowledge Hub
- Tagged with "research", "browser", "automated"

## Usage

```python
from aetheros_automation.browser_automation import ResearchMode

research = ResearchMode(browser_facade, ai_assistant)
session = await research.start_research("AI safety guidelines")
await research.add_source(session.id, "https://example.com/ai-safety")
research.add_finding(session.id, "Safety is critical", "https://example.com")
report = research.generate_report(session.id)
research.save_to_knowledge_hub(session.id)
```
