import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set
from urllib.parse import urldefrag, urlparse

import requests
from crawl4ai import (AsyncWebCrawler, BrowserConfig, CacheMode,
                      CrawlerRunConfig, CrawlResult, MemoryAdaptiveDispatcher)
from dotenv import load_dotenv
from tqdm import tqdm

MAX_CHUNK_LENGTH: int = 1000


def normalizeUrl(url) -> str:
    return urldefrag(url)[0]


# This was taken from a github repo posted by coleam00
# https://github.com/coleam00/ottomator-agents/blob/main/crawl4AI-agent-v2/insert_docs.py
async def crawlParallel(
    urls: List[str],
    max_concurrent_request: int = 5,
    max_depth: int = 5,
    crawl_urls_inside: bool = False,
) -> List[str]:
    """
    This function is used to crawl the urls provided by parallelizing
    """

    browser_config: BrowserConfig = BrowserConfig(
        headless=True,
        verbose=False,
        java_script_enabled=True,
    )

    crawl_config: CrawlerRunConfig = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS, stream=False, wait_until="networkidle"
    )

    dispatcher: MemoryAdaptiveDispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        check_interval=1.0,
        max_session_permit=max_concurrent_request,
    )

    visited: Set = set()
    current_urls: Set = set([normalizeUrl(url) for url in urls])
    markdown_results: Dict[str, str] = {}

    async with AsyncWebCrawler(config=browser_config) as crawler:

        for depth in range(max_depth):

            print(f"\n=== Crawling Depth: {depth + 1} ===")

            urls_to_crawl = list(current_urls)

            if not urls_to_crawl:
                break

            results: List[CrawlResult] = await crawler.arun_many(
                urls=urls_to_crawl, config=crawl_config, dispatcher=dispatcher
            )

            next_level_urls: Set = set()

            for result in results:

                normalized_url: str = normalizeUrl(result.url)
                visited.add(normalizeUrl)

                if result.success:
                    # print(
                    #     f"[OK] {result.url} | Markdown length: {len(result.markdown) if result.markdown else 0} chars"
                    # )

                    if result.markdown:
                        markdown_results[f"{result.url.split('/')[-1]}.txt"] = (
                            result.markdown
                        )
                    for link in result.links.get("internal", []):

                        # We are not normalizing the url over here as most of the
                        # links on ZIG documentation page for the next page is
                        # hyperlinks to a section of page, which are removed
                        # in this case.
                        next_url = link["href"]
                        if next_url not in visited and crawl_urls_inside:
                            next_level_urls.add(next_url)
                else:
                    print(f"[ERROR] {result.url}: {result.error_message}")

            if crawl_urls_inside:
                current_urls = next_level_urls
            else:
                break

    return markdown_results


if __name__ == "__main__":

    crawl_results: Dict[str, str] = {}
    crawl_results.update(
        asyncio.run(
            crawlParallel(
                ["https://ziglang.org/documentation/master/"],
                max_concurrent_request=10,
                max_depth=1,
            )
        )
    )
    crawl_results.update(
        asyncio.run(
            crawlParallel(
                ["https://ziglang.org/documentation/master/std/"],
                max_concurrent_request=10,
                max_depth=2,
                crawl_urls_inside=True,
            )
        )
    )

    # TODO: Push the resultant crawl_results documents to S3
    OUTPUT_PATH: Path = Path(".", "zig-documentations")
    if not OUTPUT_PATH.exists():
        OUTPUT_PATH.mkdir()

    for file_name, crawl_result in tqdm(crawl_results.items()):
        with open(
            Path(OUTPUT_PATH, file_name.replace("#", "")), "w", encoding="utf-8"
        ) as f:
            f.write(crawl_result)
