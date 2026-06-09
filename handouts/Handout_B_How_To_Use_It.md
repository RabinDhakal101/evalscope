# Handout B — Why This Matters and How To Use It

## Why this matters

This pruner helps Cerebras answer customer quality questions faster.

The customer wants to know:

```text
Is this model good enough for our workload?
```

Running the full benchmark every time can be costly and slow. This tool gives a smaller benchmark set that can be used first.

It helps the team decide whether a model is worth deeper testing.

## What changes for the customer team

Without this tool, the team may need to run the full benchmark before giving any answer.

With this tool, the team can run a smaller benchmark first and say:

```text
The model looks strong enough to continue.
```

or:

```text
The model looks weak, so we should not spend more time on it.
```

or:

```text
The result is close, so we should run the full benchmark before making a final call.
```

This makes the customer conversation faster and more practical.

## How to run it

Run this from the evalscope repo root.

### Coding benchmark

```powershell
python -m evalscope.pruners.benchmark_compression --reviews-dir "C:\Users\User\Evals\Evals\Part 1\reviews" --benchmark-name live_code_bench_v5 --score-key pass --file-prefix live_code_bench_v5 --target-size 60 --output lcb_pruned.json
```

### Long-context benchmark

```powershell
python -m evalscope.pruners.benchmark_compression --reviews-dir "C:\Users\User\Evals\Evals\Part 1\reviews" --benchmark-name aa_lcr --score-key acc --file-prefix aa_lcr --target-size 30 --output aalcr_pruned.json
```

The output JSON gives:

- selected sample indexes
- difficulty and disagreement for selected samples
- full benchmark score
- pruned benchmark score
- score difference

## How to read the result

If the pruned score is clearly above the customer’s required quality level, the model is a good candidate.

If the pruned score is clearly below the required quality level, the team can reject it early.

If the pruned score is close to the required level, the team should run the full benchmark.

## Why it is not random

Random sampling can miss important samples.

This pruner keeps a mix of:

- easy samples
- medium samples
- hard samples
- high-disagreement samples

High-disagreement samples are useful because they show where models differ from each other.

So the subset is more useful than a random subset of the same size.

## Multimodal value

If the customer later asks about multimodal support, random MMMU sampling may not be enough.

A better small probe should test the image encoder directly.

So I would choose samples with:

- charts
- tables
- diagrams
- small labels
- maps
- multi-panel images
- scientific images

These samples tell us whether the model is actually seeing the image properly.

## Why PMs should care

A PM or sales engineer does not need every benchmark detail.

They need to know whether the model is safe to move forward with.

This tool gives a faster first-pass answer and helps decide when to spend time on a full benchmark run.