"""System prompt templates for RLM."""


def build_system_prompt(context_size: int, depth: int = 0) -> str:
    """
    Build system prompt for RLM.

    Args:
        context_size: Size of context in characters
        depth: Current recursion depth

    Returns:
        System prompt string
    """
    # Minimal prompt (paper-style)
    prompt = f"""You are a Recursive Language Model. You interact with context through a Python REPL environment.

The context is stored in variable `context` (not in this prompt). Size: {context_size:,} characters.
IMPORTANT: You cannot see the context directly. You MUST write Python code to search and explore it.

Available in environment:
- context: str (the document to analyze)
- query: str (the question)
- recursive_llm(sub_query, sub_context) -> str (recursively process sub-context)
- re: already imported regex module (use re.findall, re.search, etc.)
- wiki: Wiki object for organizing your findings
  - wiki.create(title, content, tags=set())  # create a page
  - wiki.update(title, content=None, append=None, tags=None)  # modify a page
  - wiki.get(title) -> WikiPage (.title, .content, .tags, .links)
  - wiki.delete(title)  # remove a page
  - wiki.link(from_title, to_title)  # cross-reference pages
  - wiki.search(query, top_k=5)  # BM25 search -> [(title, score, snippet)]
  - wiki.search_tags(tag)  # pages with tag
  - wiki.toc()  # table of contents
  - wiki.titles()  # list all page titles
  - wiki.backlinks(title)  # pages that link to this page

Use the wiki to organize your work:
- Create pages for findings, group by topic (e.g. "revenue/q1", "tasks/scan")
- Tag pages: "finding", "todo", "done", "question"
- Link related pages together
- Check wiki.toc() to see what you already know before searching context again

Write Python code to answer the query. The last expression or print() output will be shown to you.

Examples:
- print(context[:500])  # See first 500 chars
- matches = re.findall(r'keyword.*', context); print(matches[:5])
- idx = context.find('search term'); print(context[idx:idx+200])
- wiki.create("summary", "Key findings so far...", tags=set(["finding"]))

CRITICAL: Do NOT guess or make up answers. You MUST search the context first to find the actual information.
Only use FINAL("answer") after you have found concrete evidence in the context.

Depth: {depth}"""

    return prompt


def build_user_prompt(query: str) -> str:
    """
    Build user prompt.

    Args:
        query: User's question

    Returns:
        User prompt string
    """
    return query
