"""Example showing RLM with wiki knowledge system and web viewer."""

import logging
import os
from dotenv import load_dotenv
from rlm import RLM
from rlm.web import serve_wiki

logging.basicConfig(level=logging.DEBUG, format="%(name)s | %(levelname)s | %(message)s")
load_dotenv()

long_document = """
The History of Artificial Intelligence

Introduction
Artificial Intelligence (AI) has transformed from a theoretical concept to a practical reality
over the past several decades. This document explores key milestones in AI development.

The 1950s: The Birth of AI
In 1950, Alan Turing published "Computing Machinery and Intelligence," introducing the famous
Turing Test. The term "Artificial Intelligence" was coined in 1956 at the Dartmouth Conference
by John McCarthy, Marvin Minsky, and others.

The 1960s-1970s: Early Optimism
During this period, researchers developed early AI programs like ELIZA (1966) and expert systems.
However, limitations in computing power led to the first "AI Winter" in the 1970s.

The 1980s-1990s: Expert Systems and Neural Networks
Expert systems became commercially successful in the 1980s. The backpropagation algorithm
revitalized neural network research in 1986.

The 2000s-2010s: Machine Learning Revolution
The rise of big data and powerful GPUs enabled deep learning breakthroughs. In 2012,
AlexNet won the ImageNet competition, marking a turning point for deep learning.

The 2020s: Large Language Models
GPT-3 (2020) and ChatGPT (2022) demonstrated unprecedented language understanding capabilities.
These models have billions of parameters and are trained on vast amounts of text data.

Conclusion
AI continues to evolve rapidly, with applications in healthcare, transportation, education,
and countless other domains. The future promises even more exciting developments.
""" * 10


def main():
    """Run RLM with wiki and web viewer."""
    rlm = RLM(
        model="gpt-5.2-codex",
        max_iterations=25,
    )

    # Start the web viewer — open http://127.0.0.1:8787 in your browser
    # to watch the wiki populate in real time as the agent works
    serve_wiki(rlm, port=8787)
    print("Wiki viewer running at http://127.0.0.1:8787")

    query = "What were the key milestones in AI development according to this document?"

    print(f"\nQuery: {query}")
    print(f"Context length: {len(long_document):,} characters")
    print("\nProcessing with RLM...\n")

    try:
        result = rlm.complete(query, long_document)

        print("\nResult:")
        print(result)

        # Inspect the wiki after completion
        print("\n--- Wiki State ---")
        print(rlm.wiki.toc())

        for title in rlm.wiki.titles():
            page = rlm.wiki.get(title)
            print(f"\n[{title}] (tags: {page.tags})")
            print(page.content[:200])

        print(f"\nStats: {rlm.stats}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found!")
        print()
        print("Please set up your API key:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your OpenAI API key to .env")
        exit(1)

    main()
