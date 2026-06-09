# Handout A — Why This Works

## What problem I solved

The customer wants to know if a model is good enough for their workload.

Their workload depends mainly on:

1. Code generation
2. Long-context reasoning

Running the full benchmark suite every time is expensive. So the goal is to choose a smaller set of samples that still gives a useful quality signal.

For this task, I focused on Part A:

- LiveCodeBench v5 for coding
- AA-LCR for long-context reasoning

The given files already have model scores, so my pruner uses those scores. It does not run live inference.

## My pruning method

I added the pruner inside evalscope here:

```text
evalscope/pruners/benchmark_compression.py
```

For every sample, I calculate two values:

```text
difficulty = average score across models
disagreement = standard deviation of model scores
```

Difficulty tells whether a question is easy, medium, or hard.

Disagreement tells whether different models behave differently on that sample.

Then the pruner selects:

- some easy samples
- some medium samples
- some hard samples
- some high-disagreement samples

This keeps the subset balanced and useful.

## Why this is better than random sampling

Random sampling may miss important samples.

For example, it may select too many easy questions, or it may miss questions where models clearly separate from each other.

My method is deterministic and score-aware. It tries to keep samples that represent the benchmark and also samples that help compare models.

It is not:

- random sampling
- easiest-only sampling
- hardest-only sampling
- hand-picked sampling

## Compression results

### LiveCodeBench v5

```text
Full benchmark: 315 samples
Pruned subset: 60 samples
Reduction: about 81%
```

My run gave this result:

```text
gpt-oss-120b   full=0.7651   pruned=0.8167   delta=+0.0516
kimi-k2.5      full=0.6286   pruned=0.5500   delta=-0.0786
minimax-m2.5   full=0.6190   pruned=0.6333   delta=+0.0143
```

### AA-LCR

```text
Full benchmark: 100 samples
Pruned subset: 30 samples
Reduction: 70%
```

My run gave this result:

```text
gpt-oss-120b   full=0.4800   pruned=0.5333   delta=+0.0533
kimi-k2.5      full=0.6600   pruned=0.7667   delta=+0.1067
minimax-m2.5   full=0.6400   pruned=0.7000   delta=+0.0600
```

## How to use the signal

This subset is not meant to fully replace the full benchmark forever.

It is meant to give a fast first-pass answer:

```text
Is this model clearly good?
Is this model clearly weak?
Is this model close enough that we need the full benchmark?
```

If the compressed benchmark result is clearly above the customer’s quality bar, the model can move forward.

If it is clearly below the bar, the model can be rejected early.

If it is close to the bar, the full benchmark should be run.

## Part B — Multimodal MMMU plan

For MMMU, I would not simply take random samples.

The customer wants to know if the model’s image encoder is good enough. So I would build a small image-encoder stress test.

I would select images that are hard for visual understanding, such as:

- charts
- tables
- small text labels
- diagrams
- maps
- multi-panel images
- geometry figures
- medical or scientific images
- low-resolution images
- images where small visual details matter

This kind of set is better than random sampling because it directly tests whether the model can read and understand the image.

## How I would test image encoder quality

Since we interact with the model through a standard OpenAI-style interface, I would use a two-step process.

First, ask the model to describe or extract the important visual information from the image.

Second, ask the model to answer the original question using that visual information.

If the model fails the first step, that suggests an image encoder problem.

If the model sees the image correctly but answers wrong, that may be more of a reasoning or knowledge problem.

## Assumptions

I assumed the three given models are enough to estimate sample difficulty and disagreement for a first version.

I also assumed that high-disagreement samples are useful because they separate model quality.

For AA-LCR, I assumed some noise may come from the LLM judge. So AA-LCR results should be treated carefully.

## What I would improve with more time

If I had more data, I would validate this on more models.

If I had a live model endpoint, I would run the pruned set on a new unseen model and compare it with the full benchmark.

If I had more time, I would add:

- bootstrap confidence intervals
- category balancing
- leave-one-model-out validation
- repeated judging for AA-LCR
- better metadata-based pruning