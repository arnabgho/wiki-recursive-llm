# Recursive Language Models (RLM)

Python implementation of Recursive Language Models for processing unbounded context lengths.

**Based on [the paper](https://alexzhang13.github.io/blog/2025/rlm/) by Alex Zhang and Omar Khattab (MIT, 2025)** | [arXiv](https://arxiv.org/abs/2512.24601)

## What is RLM?

RLM enables language models to process extremely long contexts (100k+ tokens) by:
- Storing context as a Python variable instead of in the prompt
- Allowing the LM to recursively explore and partition the context
- Providing a **wiki knowledge base** for the agent to organize findings across iterations

## Installation

```bash
git clone https://github.com/ysz/recursive-llm.git
cd recursive-llm
pip install -e .
```

## Quick Start

```bash
export OPENAI_API_KEY="sk-..."
python examples/basic_usage.py
```

```python
from rlm import RLM

rlm = RLM(model="gpt-5.2-codex", max_iterations=25)

result = rlm.complete(
    query="What are the key milestones in AI development?",
    context=long_document
)
print(result)
print(rlm.stats)
```

## Wiki Knowledge System

RLM includes a built-in wiki that the agent uses to organize its findings during exploration. Pages support tags, cross-references, and BM25 search.

### Verify the wiki works

```python
from rlm import Wiki

wiki = Wiki()

# Create pages
wiki.create("revenue/q1", "Q1 revenue was $10M, up 15% YoY", tags={"finding"})
wiki.create("revenue/q2", "Q2 revenue was $12M, up 20% YoY", tags={"finding"})
wiki.create("tasks/verify", "Need to cross-check Q2 numbers", tags={"todo"})

# Link related pages
wiki.link("tasks/verify", "revenue/q2")

# Search
print(wiki.search("revenue"))
# [('revenue/q1', 1.029, '...'), ('revenue/q2', 1.029, '...')]

# Table of contents
print(wiki.toc())
# Wiki: 3 pages
#   revenue/q1         [finding]  (iter 0)
#   revenue/q2         [finding]  (iter 0)
#   tasks/verify       [todo]    (iter 0)

# Backlinks
print(wiki.backlinks("revenue/q2"))
# ['tasks/verify']

# Tags
print(wiki.search_tags("todo"))
# ['tasks/verify']

# Export (JSON-serializable, used by web viewer)
print(wiki.export())
```

### Web Viewer

Browse the wiki in real time while the agent runs:

```python
from rlm import RLM
from rlm.web import serve_wiki

rlm = RLM(model="gpt-5.2-codex")
serve_wiki(rlm, port=8787)  # http://127.0.0.1:8787

result = rlm.complete(query="...", context=document)
```

The viewer shows a page sidebar (grouped by path prefix, filterable), page content with tags and links, a force-directed link graph, and live stats — all auto-refreshing every 2 seconds.

### How the agent uses the wiki

The wiki object is injected into the REPL environment. The agent sees it documented in its system prompt and can call any method:

```python
wiki.create("summary", "Key findings so far...", tags=set(["finding"]))
wiki.update("summary", append="\n- New data point")
wiki.search("quarterly revenue")
wiki.toc()
```

The wiki is shared across recursive calls, so a child agent's findings are visible to the parent.

## Architecture

```
RLM
├── Core (async completion loop)
├── REPL Executor (RestrictedPython sandbox)
├── Wiki (BM25-indexed knowledge base, shared across depths)
├── Web Viewer (stdlib HTTP server, single-page app)
├── Prompt Builder (system prompts with wiki API docs)
└── Parser (extract FINAL() answers)
```

## Citation

```bibtex
@misc{zhang2025rlm,
  title = {Recursive Language Models},
  author = {Zhang, Alex and Khattab, Omar},
  year = {2025},
  url = {https://alexzhang13.github.io/blog/2025/rlm/},
  eprint = {2512.24601},
  archivePrefix = {arXiv}
}
```

## License

MIT
