"""Shared venue policy and category helpers for curated AI Infra outputs."""

from __future__ import annotations

import re


VENUE_ALIASES = {
    "IEEE Trans. Parallel Distrib. Syst.": "TPDS",
    "IEEE Trans. Parallel Distributed Syst.": "TPDS",
    "ACM Trans. Comput. Syst.": "TOCS",
    "Trans. Assoc. Comput. Linguistics": "TACL",
    "Transactions of the Association for Computational Linguistics": "TACL",
    "Comput. Linguistics": "Computational Linguistics",
    "Journal of Machine Learning Research": "JMLR",
    "J. Mach. Learn. Res.": "JMLR",
    "IEEE Trans. Pattern Anal. Mach. Intell.": "TPAMI",
    "ACM Trans. Inf. Syst.": "TOIS",
    "IEEE Trans. Neural Networks Learn. Syst.": "TNNLS",
    "Artif. Intell.": "AIJ",
    "IEEE Trans. Knowl. Data Eng.": "TKDE",
    "USENIX Annual Technical Conference": "USENIX ATC",
    "Symposium on Cloud Computing": "SoCC",
    "ACM Symposium on Cloud Computing": "SoCC",
    "CrossCloud@EuroSys": "EuroSys",
    "EdgeSys@EuroSys": "EuroSys",
    "EuroMLSys@EuroSys": "EuroSys",
    "Supercomputing": "SC",
    "The Web Conference": "WWW",
    "Web Conference": "WWW",
    "LREC/COLING": "COLING",
}

VENUE_FAMILY_PATTERNS = {
    r"^ACL(?: \(\d+\)| \(Findings\)| \(Short Papers\)| \(industry\))?$": "ACL",
    r"^EMNLP(?: \(Findings\)| \(Industry Track\))?$": "EMNLP",
    r"^NAACL(?:-HLT)?(?: \(Findings\)| \(Long Papers\)| \(Short Papers\)| \(Industry Track\))?$": "NAACL",
    r"^EACL(?: \(\d+\)| \(Findings\)| \(Industry Track\)| \(Volume [12]: (?:Long|Short) Papers\))?$": "EACL",
    r"^COLING(?: \(\d+\)| \(Industry\))?$": "COLING",
    r"^KDD(?: \([12]\))?$": "KDD",
    r"^ASPLOS(?: \(\d+\))?$": "ASPLOS",
    r"^ECCV(?: \(\d+\))?$": "ECCV",
}

EXCLUDED_TRACK_PATTERNS = [
    r"(?i).*(workshop|demo|poster|tutorial|student research|system demonstration|companion volume|position paper|tiny papers).*",
    r"(?i)^ICCVW$",
    r"(?i).+@(?:CVPR|SIGCOMM|Middleware|LREC-COLING)$",
]


def normalize_venue(raw_venue: str) -> tuple[str | None, str | None]:
    """Return a display venue and optional exclusion reason.

    Main proceedings, Findings, and industry tracks are included. Workshops,
    demos, posters, tutorials, student tracks, companion volumes, and position
    papers are explicitly excluded rather than silently treated as unknown.
    """
    raw_venue = raw_venue.strip()
    if any(re.fullmatch(pattern, raw_venue) for pattern in EXCLUDED_TRACK_PATTERNS):
        return None, "non-archival or secondary track"
    if raw_venue in VENUE_ALIASES:
        return VENUE_ALIASES[raw_venue], None
    for pattern, display_name in VENUE_FAMILY_PATTERNS.items():
        if re.fullmatch(pattern, raw_venue):
            return display_name, None
    return raw_venue, None


CATEGORIES = [
    "Training Systems",
    "Inference and Serving",
    "Scheduling and Resource Management",
    "Distributed Communication and Networking",
    "Cloud and Kubernetes",
    "Accelerators, Architecture and Memory",
    "Storage and Data Pipelines",
    "Observability, Reliability and Benchmarking",
    "Efficient LLM Systems",
]


def classify_paper(title: str) -> str:
    """Assign a deterministic primary category from title-level systems signals."""
    value = title.casefold()
    rules = [
        ("Observability, Reliability and Benchmarking", ("fault", "reliab", "diagnos", "monitor", "benchmark", "verif", "straggler")),
        ("Distributed Communication and Networking", ("collective", "rdma", "network", "allreduce", "all-to-all", "communication", "roce")),
        ("Cloud and Kubernetes", ("kubernetes", "cloud", "serverless", "cross-region", "multi-tenant")),
        ("Storage and Data Pipelines", ("storage", "data pipeline", "checkpoint", "paging", "file system")),
        ("Scheduling and Resource Management", ("schedul", "resource management", "gpu sharing", "gpu pooling", "utilization", "load balanc")),
        ("Inference and Serving", ("inference", "serving", "serve", "decoding", "prefill", "kv cache")),
        ("Training Systems", ("training", "train ", "parallelism", "rlhf", "fine-tun")),
        ("Accelerators, Architecture and Memory", ("accelerator", "hardware", "pim", "npu", "memory", "tensor core", "smartnic")),
    ]
    for category, signals in rules:
        if any(signal in value for signal in signals):
            return category
    return "Efficient LLM Systems"
