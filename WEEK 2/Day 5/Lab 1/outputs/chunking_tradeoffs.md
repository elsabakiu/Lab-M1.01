# Chunking Trade-offs

## Strategy Summary
```
           strategy  avg_chunks  avg_chunk_len  avg_sentence_boundary  avg_paragraph_boundary
         Fixed-Size     128.667       1123.207                  0.115                   0.000
Recursive-Character      20.593       6514.866                  0.078                   0.001
           Semantic      63.333         97.150                  1.000                   0.000
        Token-Based      61.417       2394.487                  0.016                   0.000
```

## Notes
- Higher `avg_chunks` means more granular retrieval but more index entries.
- Higher `avg_chunk_len` means richer context per chunk but potentially noisier retrieval.
- Higher `avg_sentence_boundary` usually indicates cleaner semantic boundaries.
- Higher `avg_paragraph_boundary` suggests better paragraph-aware splits.