# Benchmark Compression Pruner

This folder explains the benchmark pruning tool added in:

```text
evalscope/pruners/benchmark_compression.py
```

## Evalscope commit SHA

I developed this work against this evalscope commit:

```text
38dd7978e16231de8ab19c4b54fc2ae49b13540b
```

## What this tool does

The customer wants to know if a model is good enough for their workload.

They mainly care about two things:

1. Code generation
2. Long-context reasoning

Running the full benchmark every time is expensive. So this tool selects a smaller set of benchmark samples, but still tries to keep the important quality signal.

The tool does not run live model inference. It uses the already provided review files and scores.

## Pruning idea

The tool keeps a mix of:

- easy samples
- medium samples
- hard samples
- high-disagreement samples

For every sample, it calculates:

```text
difficulty = average score across models
disagreement = how differently the models performed on that sample
```

Why this helps:

- Easy samples show whether the model can handle basic cases.
- Hard samples show difficult cases.
- Medium samples keep the benchmark balanced.
- High-disagreement samples are useful because they separate stronger models from weaker models.

This is not random sampling. It is also not only taking the easiest or hardest questions.

## How to run

Run these commands from the root of the evalscope repo.

### LiveCodeBench v5

```powershell
python -m evalscope.pruners.benchmark_compression --reviews-dir "C:\Users\User\Evals\Evals\Part 1\reviews" --benchmark-name live_code_bench_v5 --score-key pass --file-prefix live_code_bench_v5 --target-size 60 --output lcb_pruned.json
```

Result from my run:

```text
Benchmark: live_code_bench_v5
Full samples: 315
Selected samples: 60

gpt-oss-120b   full=0.7651   pruned=0.8167   delta=+0.0516
kimi-k2.5      full=0.6286   pruned=0.5500   delta=-0.0786
minimax-m2.5   full=0.6190   pruned=0.6333   delta=+0.0143
```

### AA-LCR

```powershell
python -m evalscope.pruners.benchmark_compression --reviews-dir "C:\Users\User\Evals\Evals\Part 1\reviews" --benchmark-name aa_lcr --score-key acc --file-prefix aa_lcr --target-size 30 --output aalcr_pruned.json
```

Result from my run:

```text
Benchmark: aa_lcr
Full samples: 100
Selected samples: 30

gpt-oss-120b   full=0.4800   pruned=0.5333   delta=+0.0533
kimi-k2.5      full=0.6600   pruned=0.7667   delta=+0.1067
minimax-m2.5   full=0.6400   pruned=0.7000   delta=+0.0600
```

## Output files

The tool creates these files:

```text
lcb_pruned.json
aalcr_pruned.json
```

Each output file contains:

- selected sample indexes
- sample difficulty
- sample disagreement
- difficulty bucket
- full score vs pruned score for each model

## Notes

This is a minimum working version.

It is useful for a fast first-pass signal. If the result is close to the customer’s required quality bar, then the full benchmark should still be run.

For AA-LCR, the score comes from an LLM judge, so some score change may come from judge noise also.