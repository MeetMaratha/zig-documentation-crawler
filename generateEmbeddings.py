import os
import re
from pathlib import Path
from typing import List

import numpy as np

MAX_LENGTH_CHUNK: int = 1000


# This was taken from a github repo posted by coleam00
# https://github.com/coleam00/ottomator-agents/blob/main/crawl4AI-agent-v2/insert_docs.py
def splitByHeader(markdown: str, header_pattern: str) -> List[str]:

    indices: List[int] = [
        m.start() for m in re.finditer(header_pattern, markdown, re.MULTILINE)
    ]
    indices.append(len(markdown))

    return [
        markdown[indices[i] : indices[i + 1]].strip() for i in range(len(indices) - 1)
    ]


# This was taken from a github repo posted by coleam00
# https://github.com/coleam00/ottomator-agents/blob/main/crawl4AI-agent-v2/insert_docs.py
def generateChunks(markdown: str, max_length: int) -> List[str]:
    """
    We generate chunks using the header tags #, ##, ###, etc.
    """

    chunks: List[str] = []

    for h1 in splitByHeader(markdown=markdown, header_pattern=r"^# .+$"):
        if len(h1) > max_length:
            # If this tag has too much information we split by ##
            for h2 in splitByHeader(markdown=h1, header_pattern=r"^## .+$"):
                # Similarly if it is too much we check for ###
                if len(h2) > max_length:
                    for h3 in splitByHeader(markdown=h2, header_pattern=r"^### .+$"):
                        # If still the text is too much we just make chunks of max length
                        if len(h3) > max_length:
                            for i in range(0, len(h3), max_length):
                                chunks.append(h3[i : i + max_length].strip())
                        else:
                            chunks.append(h3)
                else:
                    if len(h2) > max_length:
                        for i in range(0, len(h2), max_length):
                            chunks.append(h2[i : i + max_length].strip())
                    else:
                        chunks.append(h2)
        else:
            if len(h1) > max_length:
                for i in range(0, len(h1), max_length):
                    chunks.append(h1[i : i + max_length].strip())
            else:
                chunks.append(h1)

    return chunks


def embeddChunk(chunk: str) -> np.ndarray:
    return np.random.randn(1000)


if __name__ == "__main__":
    DATA_PATH: Path = Path(".", "Documenations")
    IS_QUERY: bool = False
    file_name = os.listdir(DATA_PATH)[0]

    # READ/GET the file from the S3 Bucket
    if not IS_QUERY:
        with open(Path(DATA_PATH, file_name), "r", encoding="utf-8") as f:
            data: str = f.read()
            chunks = generateChunks(data, max_length=MAX_LENGTH_CHUNK)
            print("Number of Chunks: ", len(chunks))
    else:
        chunks = [DATA_PATH]

    # Now send the chunks to the embedding endpoint
    embedded_chunks: List[np.ndarray] = []
    for chunk in chunks:
        embedded_chunks.append(embeddChunk(chunk))

    print(
        f"Number of Chunks: {len(embedded_chunks)} | Length of the last chunk: {len(embedded_chunks[-1])}"
    )
