# sa-languages-corpus

Monolingual text pipeline for 10 South African languages. Pulls from every usable public source,
cleans and sentence-splits, filters by GlotLID, dedupes globally, **excludes anything already in
`Mehgoss/sa-languages-translation`**, then pushes one config per language to
`Mehgoss/sa-languages-corpus`.

Target: 1,000,000 unique sentences per language.

## Run locally / on Colab

```bash
pip install -r requirements.txt
export HF_TOKEN=hf_xxx

python run.py fetch                 # stream raw text -> data/raw/{lang}/{source}.jsonl
python run.py process               # clean, langid, dedupe -> data/clean/{lang}.jsonl
python run.py report                # per-language counts vs the 1M target
python run.py push                  # push configs to Mehgoss/sa-languages-corpus
```

## Run on AWS

The same fetch/process logic also runs as two container-image Lambdas orchestrated
by Step Functions, so heavy sources aren't bottlenecked on a Colab session staying
alive. See **[aws/README-AWS.md](aws/README-AWS.md)** for the full setup and a
step-by-step first deploy with `sam build` / `sam deploy`.

## CI/CD

`.github/workflows/ci.yml` runs a syntax check and lints `aws/template.yaml` on
every push/PR, no AWS credentials needed. `.github/workflows/deploy-aws.yml`
runs `sam build && sam deploy` on push to `main` — set `AWS_ACCESS_KEY_ID` and
`AWS_SECRET_ACCESS_KEY` as repo secrets first (Settings → Secrets and variables
→ Actions).

Per language / per source:

```bash
python run.py fetch --langs zu xh --sources madlad400 hplt2
python run.py fetch --limit 200000        # cap raw docs per source (Colab / phone testing)
python run.py process --max 1000000       # stop at the target and move on
```

Fetch is resumable — completed `lang/source` pairs are marked in `data/state/` and skipped.
A source that 404s or has no config for a language is logged and skipped, not fatal.

Loading the result:

```python
from datasets import load_dataset
zu = load_dataset("Mehgoss/sa-languages-corpus", "zu", split="train")
```

Schema: `text`, `lang`, `source`.

## Sources

| Source | Type | Langs | Notes |
|---|---|---|---|
| MADLAD-400 (clean) | CC crawl | all 10 | Biggest single win. Document-level, audited, deduped. |
| HPLT v2 cleaned | CC + IA crawl | all 10 | 8T tokens / 193 langs. Non-overlapping with OPUS. |
| GlotCC-V1 | CC crawl | all 10 | Built specifically for long-tail langs; best nr/ss/ve recall. |
| CulturaX | CC crawl | af xh zu st tn ts nso | Heavily cleaned mC4+OSCAR. |
| mC4 | CC crawl | af xh zu st ts nso | Overlaps CulturaX; dedupe handles it. |
| Glot500-c | mixed | all 10 | Aggregated + deduped, 511 langs. |
| MzansiText | curated mix | all 10 | UCT corpus behind MzansiLM. Already filtered with DataTrove. |
| WURA | crawl + news | af zu xh st | mC4 cleaned for African langs + targeted SA news crawls. |
| Inkuba-Mono | web + news | zu xh | Lelapa, behind InkubaLM. |
| CC100 | CC crawl | af xh zu st tn nso ss | Small but clean. |
| OSCAR-2301 | CC crawl | af xh zu st tn nso | Gated — accept terms on HF first. |
| Wikipedia | encyclopedic | 9 (no nr) | High quality, low volume. |
| Vuk'uzenzele | gov magazine | all 10 | DSFSI. Small, very clean, good register. |
| ZA-gov-multilingual | gov docs | all 10 | DSFSI. |
| SA-Monolingual-Corpora | gov pubs | zu xh st nso | UCT thesis corpus. |
| PuoData | curated | tn | Best Setswana resource available. |
| Leipzig Corpora | web/news/wiki | all 10 | Pre-split sentences. Only public source with real nr coverage. |

### Not wired up (manual, worth doing)

- **NCHLT Text Corpora** (SADiLaR) — all 11 languages, ~9.8M words, the cleanest SA text
  that exists. DSpace REST at `hdl.handle.net/20.500.12185/1`. Same REST route used for
  Autshumato on the parallel corpus.
- **Autshumato monolingual** — af 1.19M segments, xh 341k, zu 239k, nr 83k.
  Partly already consumed by the parallel corpus; the exclusion step will drop the overlap.
- **Isolezwe** (isiZulu daily, via Newstools) — largest African-language newspaper archive in SA.
- **eBible / biblenlp-corpus** — ~31k verses per language, all 10. Formal register but
  it's real volume for nr, ss, ve.
- **SABC / SAnews.gov.za / Ligwalagwala FM / Phalaphala FM / Munghana Lonene** — the low-resource
  languages only get to 1M via targeted news scraping. Nothing public gets ve/ss/nr there.

## Realistic yields

Honest read on the 1M-per-language target from public sources:

| Language | Code | Expected unique sentences | 1M target |
|---|---|---|---|
| Afrikaans | af | 50M+ | easily |
| isiZulu | zu | 5–15M | yes |
| isiXhosa | xh | 3–8M | yes |
| Sesotho | st | 2–5M | yes |
| Setswana | tn | 1–3M | yes |
| Sepedi | nso | 0.8–2M | likely |
| Xitsonga | ts | 0.4–1.2M | borderline |
| Tshivenda | ve | 0.3–0.8M | no, needs scraping |
| siSwati | ss | 0.2–0.6M | no, needs scraping |
| isiNdebele | nr | 0.1–0.3M | no, needs scraping |

The four at the bottom are the whole problem. Everything public has already been crawled;
getting them to 1M means scraping SA broadcast/news sites directly or back-translating.

## Language ID

GlotLID (`cis-lmu/glotlid`) — the only LID model that separates the Nguni languages properly.
Confidence threshold is 0.70 for nr/ss/zu/xh/st/nso/tn (crawl data mislabels isiNdebele and
siSwati as isiZulu constantly), 0.50 elsewhere. `--skip-langid` bypasses it for quick tests but
will pollute the low-resource configs.

## Dedup

Two layers, both on a normalized key (NFKC, lowercased, punctuation stripped, whitespace collapsed):

1. Within-corpus, across all sources.
2. Against `Mehgoss/sa-languages-translation` — the target-side sentences of the parallel corpus
   are hashed into a sorted uint64 array cached in `data/state/exclude.{lang}.npy` and every
   candidate is checked against it. Nothing already used for the first training run gets repeated.

If the parallel repo's config names aren't `{lang}-en`, pass the right ones into
`process.build_exclusion(lang, configs=[...])`.
