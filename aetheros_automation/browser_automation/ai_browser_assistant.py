from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AIBrowserAssistant:
    def __init__(self, browser_facade):
        self._browser_facade = browser_facade
        self._conversation: list[dict[str, str]] = []

    async def process_query(self, query: str, session_id: str, tab_id: str) -> dict[str, Any]:
        query_lower = query.lower()
        tab = self._browser_facade.tab_manager.get_tab(session_id, tab_id)
        if tab is None:
            return {"error": "Tab not found", "response": "I could not find the active tab."}

        browser = self._browser_facade.browser_manager._sessions.get(session_id)
        if browser is None:
            return {"error": "Browser not found", "response": "No browser session is active."}

        self._conversation.append({"role": "user", "content": query})

        if "summarize" in query_lower or "summary" in query_lower:
            return await self._handle_summarize(browser, tab)
        elif "extract" in query_lower and "email" in query_lower:
            return await self._handle_extract_emails(browser, tab)
        elif "extract" in query_lower and ("link" in query_lower or "url" in query_lower):
            return await self._handle_extract_links(browser, tab)
        elif "price" in query_lower or "cheapest" in query_lower or "compare" in query_lower:
            return await self._handle_prices(browser, tab, query)
        elif "translate" in query_lower:
            return await self._handle_translate(browser, tab, query)
        elif "read" in query_lower and ("article" in query_lower or "to me" in query_lower):
            return await self._handle_read_article(browser, tab)
        elif "documentation" in query_lower or "docs" in query_lower:
            return await self._handle_find_documentation(browser, tab, query)
        elif "form" in query_lower:
            return await self._handle_form_analysis(browser, tab)
        elif "search" in query_lower:
            return await self._handle_search(browser, tab, query)
        elif "find" in query_lower:
            return await self._handle_find(browser, tab, query)
        else:
            return await self._handle_general_query(browser, tab, query)

    async def _handle_summarize(self, browser, tab) -> dict[str, Any]:
        page_text = await browser.read_page()
        url = await browser.get_url()
        analyzer = self._browser_facade.page_analyzer
        analysis = await analyzer.analyze_page(browser)
        summary = analysis.meta_description or analyzer.generate_summary(analysis)
        response = (
            f"**Page Summary**\n\n"
            f"**URL:** {url}\n"
            f"**Title:** {analysis.title}\n"
            f"**Word Count:** {analysis.word_count} words\n"
            f"**Reading Time:** ~{analysis.reading_time_minutes} min\n\n"
            f"**Summary:**\n{summary}\n"
        )
        if analysis.key_points:
            response += "\n**Key Points:**\n" + "\n".join(f"- {p}" for p in analysis.key_points[:5])
        self._conversation.append({"role": "assistant", "content": response})
        return {"response": response, "analysis": analysis}

    async def _handle_extract_emails(self, browser, tab) -> dict[str, Any]:
        analyzer = self._browser_facade.page_analyzer
        analysis = await analyzer.analyze_page(browser)
        if analysis.emails:
            response = "**Extracted Email Addresses:**\n" + "\n".join(f"- {e}" for e in analysis.emails)
        else:
            response = "No email addresses found on this page."
        self._conversation.append({"role": "assistant", "content": response})
        return {"response": response, "emails": analysis.emails}

    async def _handle_extract_links(self, browser, tab) -> dict[str, Any]:
        links = await browser.execute_js(
            "() => Array.from(document.querySelectorAll('a[href]')).map(a => ({href: a.href, text: a.innerText.trim().slice(0, 100)}))"
        )
        if isinstance(links, list):
            links = [l for l in links if l.get("href", "").startswith("http")]
            response = f"**Extracted Links ({len(links)}):**\n"
            for link in links[:20]:
                response += f"- [{link.get('text', 'Link')}]({link['href']})\n"
            if len(links) > 20:
                response += f"\n*...and {len(links) - 20} more*"
        else:
            response = "Could not extract links from this page."
        self._conversation.append({"role": "assistant", "content": response})
        return {"response": response, "links": links if isinstance(links, list) else []}

    async def _handle_prices(self, browser, tab, query: str) -> dict[str, Any]:
        analyzer = self._browser_facade.page_analyzer
        analysis = await analyzer.analyze_page(browser)
        if analysis.prices:
            response = "**Prices Found:**\n" + "\n".join(f"- {p}" for p in analysis.prices[:20])
        else:
            response = "No prices found on this page. Try searching for specific products."
        self._conversation.append({"role": "assistant", "content": response})
        return {"response": response, "prices": analysis.prices}

    async def _handle_translate(self, browser, tab, query: str) -> dict[str, Any]:
        page_text = await browser.read_page()
        lines = [l.strip() for l in page_text.split("\n") if l.strip() and len(l.strip()) > 20]
        sample = "\n\n".join(lines[:5])
        response = f"**Translation Request**\n\nPage text is ready for translation ({len(page_text)} characters).\n\nSample:\n```\n{sample[:1000]}\n```\n\nTo translate this page, please use the AI translation feature or configure a translation provider."
        self._conversation.append({"role": "assistant", "content": response})
        return {"response": response}

    async def _handle_read_article(self, browser, tab) -> dict[str, Any]:
        analyzer = self._browser_facade.page_analyzer
        analysis = await analyzer.analyze_page(browser)
        articles = await analyzer.extract_articles(browser)
        if articles:
            content = articles[0]["content"]
        else:
            content = analysis.text_content
        response = f"**Article Reader**\n\n**{analysis.title}**\n\n{content[:2000]}"
        if len(content) > 2000:
            response += f"\n\n*...article continues ({len(content) - 2000} more characters)*"
        self._conversation.append({"role": "assistant", "content": response})
        return {"response": response, "content": content}

    async def _handle_find_documentation(self, browser, tab, query: str) -> dict[str, Any]:
        url = await browser.get_url()
        page_text = await browser.read_page()
        if "docs" in url.lower() or "documentation" in url.lower():
            response = f"You are already on documentation at {url}."
        else:
            response = f"Looking for official documentation related to '{query}'.\n\nCurrent page: {url}\n\nI can search for documentation using the web search feature."
        self._conversation.append({"role": "assistant", "content": response})
        return {"response": response}

    async def _handle_form_analysis(self, browser, tab) -> dict[str, Any]:
        forms = await browser.execute_js(
            """() => Array.from(document.querySelectorAll('form')).map((form, i) => ({
                index: i,
                action: form.action || '',
                method: form.method || 'get',
                fields: Array.from(form.querySelectorAll('input, select, textarea')).map(el => ({
                    name: el.name || el.id || '',
                    type: el.type || el.tagName.toLowerCase(),
                    placeholder: el.placeholder || '',
                    required: el.required || false
                }))
            }))"""
        )
        if isinstance(forms, list) and forms:
            response = f"**Forms Found: {len(forms)}**\n\n"
            for form in forms:
                response += f"Form #{form['index'] + 1}: action={form['action']}, method={form['method']}\n"
                for field in form["fields"]:
                    req = " (required)" if field["required"] else ""
                    response += f"  - {field['name']}: {field['type']}{req}\n"
        else:
            response = "No forms found on this page."
        self._conversation.append({"role": "assistant", "content": response})
        return {"response": response, "forms": forms if isinstance(forms, list) else []}

    async def _handle_search(self, browser, tab, query: str) -> dict[str, Any]:
        import re as re_module

        m = re_module.search(r'search\s+(?:for\s+)?["\']?(.+?)["\']?$', query, re_module.IGNORECASE)
        search_term = m.group(1) if m else query.replace("search", "").strip()
        if not search_term or search_term == query:
            search_term = query.replace("search", "").strip()
        search_url = self._browser_facade.web_search_manager.get_search_url(search_term)
        await browser.navigate(search_url)
        response = f"Searched for '{search_term}' using {self._browser_facade.web_search_manager._active_provider}."
        self._browser_facade.web_search_manager.record_search(search_term)
        self._conversation.append({"role": "assistant", "content": response})
        return {"response": response, "search_term": search_term}

    async def _handle_find(self, browser, tab, query: str) -> dict[str, Any]:
        import re as re_module

        m = re_module.search(r'find\s+(.+?)(?:\s+on\s+this\s+page)?$', query, re_module.IGNORECASE)
        term = m.group(1) if m else query.replace("find", "").strip()
        result = await browser.execute_js(
            f"() => {{ const matches = document.body.innerText.match(new RegExp('{re_module.escape(term)}', 'gi')); return matches ? matches.length : 0; }}"
        )
        if isinstance(result, (int, float)) and result > 0:
            response = f"Found **{result}** occurrence(s) of '{term}' on this page."
        else:
            response = f"No matches found for '{term}' on this page."
        self._conversation.append({"role": "assistant", "content": response})
        return {"response": response}

    async def _handle_general_query(self, browser, tab, query: str) -> dict[str, Any]:
        page_text = await browser.read_page()
        url = await browser.get_url()
        response = f"**Current Page:** {url}\n\nPage content is loaded. I can help with:\n- Summarize this page\n- Extract emails, links, or prices\n- Compare products\n- Find documentation\n- Translate content\n- Analyze forms\n- Search for something\n\nWhat would you like me to do?"
        self._conversation.append({"role": "assistant", "content": response})
        return {"response": response}

    def get_conversation(self) -> list[dict[str, str]]:
        return list(self._conversation)

    def clear_conversation(self):
        self._conversation.clear()
