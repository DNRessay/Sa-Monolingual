from pathlib import Path

HF_REPO = "Mehgoss/sa-languages-corpus"
PARALLEL_REPO = "Mehgoss/sa-languages-translation"

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
STATE = ROOT / "data" / "state"

LANGS = ["af", "nr", "nso", "ss", "st", "tn", "ts", "ve", "xh", "zu"]

LANG_NAMES = {
    "af": "Afrikaans",
    "nr": "isiNdebele",
    "nso": "Sepedi",
    "ss": "siSwati",
    "st": "Sesotho",
    "tn": "Setswana",
    "ts": "Xitsonga",
    "ve": "Tshivenda",
    "xh": "isiXhosa",
    "zu": "isiZulu",
}

GLOTLID = {
    "af": "afr_Latn",
    "nr": "nbl_Latn",
    "nso": "nso_Latn",
    "ss": "ssw_Latn",
    "st": "sot_Latn",
    "tn": "tsn_Latn",
    "ts": "tso_Latn",
    "ve": "ven_Latn",
    "xh": "xho_Latn",
    "zu": "zul_Latn",
}

# Nguni langs get badly confused with each other in web crawls; keep these strict.
STRICT_LANGID = {"nr", "ss", "zu", "xh", "st", "nso", "tn"}

# kind=hf  -> streamed via datasets.load_dataset(repo, config, split, streaming=True)
# kind=url -> plain HTTP file (txt / txt.gz / zip containing txt)
SOURCES = [
    {
        "name": "madlad400",
        "kind": "hf",
        "repo": "allenai/madlad-400",
        "split": "clean",
        "field": "text",
        "trust": True,
        "configs": {
            "af": "af", "nr": "nr", "nso": "nso", "ss": "ss", "st": "st",
            "tn": "tn", "ts": "ts", "ve": "ve", "xh": "xh", "zu": "zu",
        },
    },
    {
        "name": "hplt2",
        "kind": "hf",
        "repo": "HPLT/HPLT2.0_cleaned",
        "split": "train",
        "field": "text",
        "configs": {
            "af": "afr_Latn", "nso": "nso_Latn", "st": "sot_Latn", "ss": "ssw_Latn",
            "tn": "tsn_Latn", "ts": "tso_Latn", "ve": "ven_Latn", "xh": "xho_Latn",
            "zu": "zul_Latn", "nr": "nbl_Latn",
        },
    },
    {
        "name": "culturax",
        "kind": "hf",
        "repo": "uonlp/CulturaX",
        "split": "train",
        "field": "text",
        "configs": {"af": "af", "xh": "xh", "zu": "zu", "st": "st", "tn": "tn", "ts": "ts", "nso": "ns"},
    },
    {
        "name": "mc4",
        "kind": "hf",
        "repo": "allenai/c4",
        "split": "train",
        "field": "text",
        "data_dir_tpl": "multilingual",
        "configs": {"af": "af", "xh": "xh", "zu": "zu", "st": "st", "ts": "ts", "nso": "ns"},
    },
    {
        "name": "glot500",
        "kind": "hf",
        "repo": "cis-lmu/Glot500",
        "split": "train",
        "field": "text",
        "configs": {
            "af": "afr_Latn", "nr": "nbl_Latn", "nso": "nso_Latn", "ss": "ssw_Latn",
            "st": "sot_Latn", "tn": "tsn_Latn", "ts": "tso_Latn", "ve": "ven_Latn",
            "xh": "xho_Latn", "zu": "zul_Latn",
        },
    },
    {
        "name": "glotcc",
        "kind": "hf",
        "repo": "cis-lmu/GlotCC-V1",
        "split": "train",
        "field": "content",
        "configs": {
            "af": "afr-Latn", "nr": "nbl-Latn", "nso": "nso-Latn", "ss": "ssw-Latn",
            "st": "sot-Latn", "tn": "tsn-Latn", "ts": "tso-Latn", "ve": "ven-Latn",
            "xh": "xho-Latn", "zu": "zul-Latn",
        },
    },
    {
        "name": "mzansitext",
        "kind": "hf",
        "repo": "anrilombard/mzansi-text",
        "split": "train",
        "field": "text",
        "configs": {
            "af": "afr", "nr": "nbl", "nso": "nso", "ss": "ssw", "st": "sot",
            "tn": "tsn", "ts": "tso", "ve": "ven", "xh": "xho", "zu": "zul",
        },
    },
    {
        "name": "wura",
        "kind": "hf",
        "repo": "castorini/wura",
        "split": "train",
        "field": "text",
        "configs": {"af": "afr", "zu": "zul", "xh": "xho", "st": "sot"},
    },
    {
        "name": "inkuba_mono",
        "kind": "hf",
        "repo": "lelapa/Inkuba-Mono",
        "split": "train",
        "field": "text",
        "configs": {"zu": "zul", "xh": "xho"},
    },
    {
        "name": "cc100",
        "kind": "hf",
        "repo": "cc100",
        "split": "train",
        "field": "text",
        "configs": {"af": "af", "xh": "xh", "zu": "zu", "st": "st", "tn": "tn", "nso": "ns", "ss": "ss"},
    },
    {
        "name": "oscar2301",
        "kind": "hf",
        "repo": "oscar-corpus/OSCAR-2301",
        "split": "train",
        "field": "text",
        "configs": {"af": "af", "xh": "xh", "zu": "zu", "st": "st", "tn": "tn", "nso": "nso"},
    },
    {
        "name": "wikipedia",
        "kind": "hf",
        "repo": "wikimedia/wikipedia",
        "split": "train",
        "field": "text",
        "configs": {
            "af": "20231101.af", "nso": "20231101.nso", "ss": "20231101.ss",
            "st": "20231101.st", "tn": "20231101.tn", "ts": "20231101.ts",
            "ve": "20231101.ve", "xh": "20231101.xh", "zu": "20231101.zu",
        },
    },
    {
        "name": "vukuzenzele",
        "kind": "hf",
        "repo": "dsfsi/vukuzenzele-monolingual",
        "split": "train",
        "field": "text",
        "configs": {
            "af": "afr", "nr": "nbl", "nso": "nso", "ss": "ssw", "st": "sot",
            "tn": "tsn", "ts": "tso", "ve": "ven", "xh": "xho", "zu": "zul",
        },
    },
    {
        "name": "za_gov",
        "kind": "hf",
        "repo": "dsfsi/za-gov-multilingual",
        "split": "train",
        "field": "text",
        "configs": {
            "af": "afr", "nr": "nbl", "nso": "nso", "ss": "ssw", "st": "sot",
            "tn": "tsn", "ts": "tso", "ve": "ven", "xh": "xho", "zu": "zul",
        },
    },
    {
        "name": "sa_mono_uct",
        "kind": "hf",
        "repo": "sello-ralethe/SA-Monolingual-Corpora",
        "split": "train",
        "field": "text",
        "configs": {"zu": "isizulu", "xh": "isixhosa", "st": "sesotho", "nso": "sepedi"},
    },
    {
        "name": "puodata",
        "kind": "hf",
        "repo": "dsfsi/PuoData",
        "split": "train",
        "field": "text",
        "configs": {"tn": "default"},
    },
    {
        "name": "leipzig",
        "kind": "url",
        "configs": {
            "af": ["https://downloads.wortschatz-leipzig.de/corpora/afr_mixed_2012_1M.tar.gz",
                   "https://downloads.wortschatz-leipzig.de/corpora/afr-za_web_2019_1M.tar.gz"],
            "zu": ["https://downloads.wortschatz-leipzig.de/corpora/zul_wikipedia_2021_300K.tar.gz",
                   "https://downloads.wortschatz-leipzig.de/corpora/zul-za_web_2019_300K.tar.gz"],
            "xh": ["https://downloads.wortschatz-leipzig.de/corpora/xho-za_web_2019_300K.tar.gz"],
            "st": ["https://downloads.wortschatz-leipzig.de/corpora/sot-za_web_2019_100K.tar.gz"],
            "tn": ["https://downloads.wortschatz-leipzig.de/corpora/tsn-za_web_2019_100K.tar.gz"],
            "nso": ["https://downloads.wortschatz-leipzig.de/corpora/nso-za_web_2019_100K.tar.gz"],
            "ts": ["https://downloads.wortschatz-leipzig.de/corpora/tso-za_web_2019_100K.tar.gz"],
            "ve": ["https://downloads.wortschatz-leipzig.de/corpora/ven-za_web_2019_30K.tar.gz"],
            "ss": ["https://downloads.wortschatz-leipzig.de/corpora/ssw-za_web_2019_30K.tar.gz"],
            "nr": ["https://downloads.wortschatz-leipzig.de/corpora/nbl-za_web_2019_10K.tar.gz"],
        },
    },
]

MIN_WORDS = 3
MAX_WORDS = 120
MIN_CHARS = 20
MAX_CHARS = 1000
MIN_ALPHA_RATIO = 0.70
MAX_DIGIT_RATIO = 0.20
LANGID_THRESHOLD = 0.50
LANGID_THRESHOLD_STRICT = 0.70
