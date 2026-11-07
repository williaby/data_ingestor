---
description: "Level 0 pointer: where data_ingestor sits in the Foundry pipeline."
status: active
---

# Level 0: Foundry Pipeline Context

The canonical Level 0 page is [pipeline-level-0.md](../../pipeline-level-0.md). It is identical in all five pipeline
repositories, so this repository does not copy its diagram.

In that diagram, this repository (`data_ingestor`) is the **Chunk** box, the last stage of the pipeline. Chunk reads
`DoclingDOM.json` from Unify (`03-docling-dom/`) and writes `RAGChunkSet.json` (`04-chunks/`). The pipeline ends at
chunks; embedding, vector storage, and search belong to downstream applications.

Next level: [Level 1: Chunk stage architecture](../level-1/index.md).
