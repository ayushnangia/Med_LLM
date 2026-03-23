# RAG vs Prompt (GPT-5.2 judge)

| Model | Old Correct | RAG Correct | Delta | Old Clinical OK | RAG Clinical OK | Delta | Old Avg Overall | RAG Avg Overall | Delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| google_gemma-3-27b-it | 5/11 | 4/11 | -1 | 9/11 | 10/11 | +1 | 0.631 | 0.604 | -0.027 |
| google_gemma-3-4b-it | 0/11 | 1/11 | +1 | 3/11 | 5/11 | +2 | 0.300 | 0.424 | +0.124 |
| openmeditron_meditron3-qwen2.5-7b | 1/11 | 1/11 | +0 | 2/11 | 2/11 | +0 | 0.283 | 0.354 | +0.071 |
| allenai_olmo-3.1-32b-instruct | 4/11 | 3/11 | -1 | 5/11 | 6/11 | +1 | 0.534 | 0.535 | +0.002 |
| allenai_olmo-3.1-32b-think | 4/11 | 4/11 | +0 | 7/11 | 6/11 | -1 | 0.588 | 0.570 | -0.018 |