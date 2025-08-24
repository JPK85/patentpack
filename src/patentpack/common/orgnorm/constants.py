from __future__ import annotations

import re

# Shared low‑level regex/constants
SPACE_RE = re.compile(r"\s+")
TRAILING_SLASH_TAG_RE = re.compile(
    r"/(?:the|[A-Z]{2})$", re.I
)  # drop '/NY','/DE','/The', etc.
ADR_SUFFIX_RE = re.compile(
    r"(?:\s*[-,]?\s*(?:adr(?:hedged)?|ads|gdr)(?:\s*\([^)]*\))?\s*)+$", re.I
)
ASCII_PAT = re.compile(r"[A-Za-z]")

# Corporate/legal suffixes used for stemming
SUFFIX_RE = re.compile(
    r"\b("
    r"incorporated|inc|corp(?:oration)?|co(?:mpany)?|ltd|limited|llc|plc|"
    r"a\.?g\.?|ag|se|s\.?e\.?|"
    r"n\.?v\.?|nv|oy|oyj|oy\.?j\.?|ab|gmbh|kgaa|kg|"
    r"s\.?a\.?|sa|s\.?a\.?s\.?|sas|s\.?a\.?u\.?|"
    r"s\.?l\.?u?\.?|"
    r"s\.?p\.?a\.?|spa|bv|b\.?v\.?|bvba|asa|as|"
    r"pte|pty|aps|a/?s|"
    r"k\.?k\.?|kk|kabushiki\s*kaisha|"
    r"aktiengesellschaft|"
    r"aktiebolag|aktiebolaget|publ|"
    r"societa\s+per\s+azioni|società\s+per\s+azioni|"
    r"societe\s+anonyme|société\s+anonyme"
    r")\b\.?",
    flags=re.I,
)

# “ADR” signal (also used by match/search logic)
ADR_PAT = re.compile(r"\b(adr|ads|gdr)\b|depositar|adrhedged", re.I)

# Comparison stopwords (kept tiny & conservative)
STOPWORDS = {"the"}

# Undotted→canonical dotted short-forms (for generating dotted/undotted variants)
DOTTING_MAP = {
    # Anglo
    "INC": "Inc.",
    "CORP": "Corp.",
    "CO": "Co.",
    "PLC": "P.L.C.",
    # NL / BE
    "BV": "B.V.",
    "NV": "N.V.",
    # FR / ES / many
    "SA": "S.A.",
    "SAS": "S.A.S.",
    "SAU": "S.A.U.",
    "SL": "S.L.",
    "SLU": "S.L.U.",
    # IT
    "SRL": "S.r.l.",
    # CZ / SK
    "SRO": "S.r.o.",
    # FI
    "OY": "O.Y.",
    "OYJ": "O.Y.J.",
    # NO
    "AS": "A.S.",
    "ASA": "A.S.A.",
    # EU
    "SE": "S.E.",
    # JP
    "KK": "K.K.",
    # DE (rarely dotted in some data)
    "GMBH": "G.m.b.H.",
}

# Short suffix → fully spelled form (for retrieval variants)
SUFFIX_TO_FULL = {
    "ag": "Aktiengesellschaft",
    "ab": "Aktiebolag",
    "nv": "Naamloze Vennootschap",
    "s.p.a.": "Società per Azioni",
    "spa": "Società per Azioni",
    "sa": "Société Anonyme",
    "ltd": "Limited",
    "plc": "Public Limited Company",
    "co": "Company",
    "inc": "Incorporated",
    "llc": "Limited Liability Company",
    "gmbh": "Gesellschaft mit beschränkter Haftung",
    "kgaa": "Kommanditgesellschaft auf Aktien",
    "kg": "Kommanditgesellschaft",
    "oy": "Osakeyhtiö",
    "corp": "Corporation",
}

# Country hints keyed by short suffix token
SUFFIX_COUNTRY_HINTS = {
    "ag": ["DE", "AT", "CH"],
    "ab": ["SE"],
    "nv": ["NL", "BE"],
    "s.p.a.": ["IT"],
    "spa": ["IT"],
    "sa": ["FR", "BE", "LU", "CH", "ES"],
    "oy": ["FI"],
    "oyj": ["FI"],
}
