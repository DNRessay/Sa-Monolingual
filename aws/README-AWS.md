# Running this on AWS with SAM

## What SAM actually is

SAM (Serverless Application Model) is a CLI on top of CloudFormation. You describe
resources — Lambda functions, an S3 bucket, a Step Functions state machine — in one
YAML file (`aws/template.yaml`), and the CLI turns that into a CloudFormation stack:
builds your code/images, uploads them, and creates or updates every resource in one
atomic operation. `sam build` packages things, `sam deploy` ships them, `sam delete`
tears the whole stack down again. That's the entire mental model.

## What's actually in this stack

- **DataBucket** (S3) — everything lives here: `raw/{lang}/{source}/part-*.jsonl`,
  then `clean/{lang}.jsonl`.
- **FetchFunction** (Lambda, container image) — given `{lang, source, skip, chunk}`,
  streams up to `chunk` rows starting at `skip` from one source, uploads the shard,
  and reports back `next_skip` and whether the source is exhausted.
- **ProcessFunction** (Lambda, container image) — given `{lang}`, downloads every raw
  shard for that language from S3, cleans/langid-filters/dedupes it, uploads
  `clean/{lang}.jsonl`.
- **PipelineStateMachine** (Step Functions) — fans out FetchFunction across every
  (language, source) pair, looping each one in a chunk-skip-repeat cycle until it's
  exhausted or hits a safety cap, then fans out ProcessFunction across all 10
  languages. Open it in the AWS Console → Step Functions → this state machine →
  an execution, and you get a live graph of exactly what's running. That console
  view is genuinely the best way to learn what's actually happening.

Both Lambdas are **container images**, not zip packages — `datasets`, `numpy`, and
`fasttext` are too heavy for a plain zip. That's why the Dockerfiles exist and why
you need Docker running locally to build.

## Prerequisites

1. An AWS account, with an IAM user that has enough permission to create Lambda,
   S3, Step Functions, and IAM resources (for a personal account, `AdministratorAccess`
   while learning is fine; tighten later).
2. AWS CLI installed and configured: `aws configure` — it'll ask for an access key,
   secret key, and default region (use `eu-west-1`).
3. Docker installed and running (`sam build` uses it to build the Lambda images).
4. AWS SAM CLI installed:
   - macOS: `brew install aws-sam-cli`
   - Linux: see https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html

Check everything's in place: `sam --version`, `docker ps`, `aws sts get-caller-identity`.

## First deploy

From the repo root:

```bash
sam build -t aws/template.yaml
sam deploy --guided --template aws/template.yaml
```

`--guided` walks you through prompts the first time: stack name (accept the
default, `sa-languages-corpus`), region (`eu-west-1`), whether to allow SAM to
create IAM roles (yes), and whether to save these answers to `aws/samconfig.toml`
(yes — after that, `sam deploy` alone reuses them).

This takes a few minutes the first time (building two container images and
pushing them to ECR). When it finishes, note the `BucketName` and
`StateMachineArn` values in the Outputs section — you'll need them next.

## Running the pipeline

Generate the execution input (every (language, source) pair, plus the language
list) from `config.py`:

```bash
PYTHONPATH=. python aws/generate_pairs.py --out stepfunctions-input.json
```

Start an execution:

```bash
aws stepfunctions start-execution \
  --state-machine-arn <StateMachineArn from the outputs> \
  --input file://stepfunctions-input.json
```

Watch it:

```bash
aws stepfunctions describe-execution --execution-arn <arn from the previous command>
```

Or just open the Step Functions console — the running graph is worth watching
once.

Check what landed:

```bash
aws s3 ls s3://<BucketName>/clean/
```

## Pushing to Hugging Face

`push.py` still runs locally/on Colab, not on AWS — it needs your `HF_TOKEN` and
it's a one-person action, not something worth automating yet. Pull the clean
files down and push as before:

```bash
aws s3 sync s3://<BucketName>/clean/ data/clean/
export HF_TOKEN=hf_xxx
python push.py
```

## Cost

Nothing runs, nothing costs anything, until you start a Step Functions execution.
No VPC and no NAT gateway are used, so idle cost is just S3 storage (cents/month
for this volume) plus the tiny Step Functions/Lambda request cost when you
actually run it. The real cost driver is Lambda compute time on the big crawl
sources — budget for it, or lower `chunk`/the iteration cap in
`aws/statemachine.asl.json` to bound a single execution's spend.

**Clean up when you're done experimenting:**

```bash
sam delete --stack-name sa-languages-corpus
```

This deletes the Lambda functions, the state machine, and the S3 bucket (you'll
be prompted since the bucket may have objects in it).

## Honest limits of this design

- **Lambda's hard 15-minute timeout** is why fetch is chunked at 200k rows/chunk
  with up to 25 resume-iterations per execution (5M rows per source/language
  ceiling, per run). MADLAD-400 and HPLT2 are far bigger than that for
  high-resource languages like Afrikaans — draining them fully means running
  the state machine more than once, or raising the iteration cap in
  `statemachine.asl.json`.
- Some HF dataset formats (parquet-backed) fetch whole remote shard files even
  in "streaming" mode, which can spike a single Lambda invocation's disk use.
  Ephemeral storage is set to the Lambda max (10GB) to absorb this, but a single
  oversized shard could still fail — it'll just retry via the state machine's
  `Retry` block, and worst case that (lang, source) pair needs a manual re-run
  with a smaller `chunk`.
- If a language's raw shards outgrow ProcessFunction's disk/memory (10GB /
  8GB), the next step up is AWS Batch or Fargate instead of Lambda — same
  container image, no 15-minute wall clock. Not built here; flagging it so
  you know where the ceiling is.
