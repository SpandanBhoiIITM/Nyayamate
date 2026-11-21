"""Curated list of Indian laws and official resources the AI is ALLOWED to name.

Only act names and official portals are listed – no section numbers – because
section-level accuracy cannot be guaranteed by this prototype. Anything the
model cites that is not on this list is flagged as unverified in the UI.

Last reviewed: November 2026. Users should always confirm the current text on
India Code (https://www.indiacode.nic.in).
"""
from __future__ import annotations

VERIFIED_LAWS = [
    {
        "name": "Consumer Protection Act, 2019",
        "aliases": ["consumer protection act, 2019", "consumer protection act 2019"],
        "areas": ["consumer"],
        "note": "Central law on consumer rights, unfair trade practices, and consumer "
                "commissions at district, state and national level.",
        "source": "https://www.indiacode.nic.in",
    },
    {
        "name": "Consumer Protection (E-Commerce) Rules, 2020",
        "aliases": ["e-commerce rules, 2020", "consumer protection (e-commerce) rules"],
        "areas": ["consumer"],
        "note": "Rules made under the Consumer Protection Act, 2019 that apply to online "
                "sellers and marketplaces, including grievance redressal.",
        "source": "https://consumeraffairs.nic.in",
    },
    {
        "name": "Code on Wages, 2019",
        "aliases": ["code on wages, 2019", "code on wages 2019", "wage code"],
        "areas": ["employment"],
        "note": "Brought into force from 21 November 2025 with the other three labour codes. "
                "It replaced the Payment of Wages Act, 1936, the Minimum Wages Act, 1948, the "
                "Payment of Bonus Act, 1965 and the Equal Remuneration Act, 1976. Some rules "
                "(central and state) may still be pending – verify current status.",
        "source": "https://labour.gov.in",
    },
    {
        "name": "Indian Contract Act, 1872",
        "aliases": ["indian contract act, 1872", "indian contract act 1872", "contract act"],
        "areas": ["tenancy", "employment", "consumer", "general"],
        "note": "General law on agreements, including obligations under rental and "
                "employment agreements.",
        "source": "https://www.indiacode.nic.in",
    },
    {
        "name": "Model Tenancy Act, 2021",
        "aliases": ["model tenancy act, 2021", "model tenancy act 2021", "model tenancy act"],
        "areas": ["tenancy"],
        "note": "A MODEL law circulated by the Central Government. It applies only in states "
                "that have adopted it; otherwise the state's own rent control law applies. "
                "Always check which law applies in your state.",
        "source": "https://mohua.gov.in",
    },
    {
        "name": "Legal Services Authorities Act, 1987",
        "aliases": ["legal services authorities act, 1987", "legal services authorities act"],
        "areas": ["general"],
        "note": "Basis for free legal aid through NALSA, State and District Legal Services "
                "Authorities, and Lok Adalats.",
        "source": "https://nalsa.gov.in",
    },
    {
        "name": "Bharatiya Nyaya Sanhita, 2023",
        "aliases": ["bharatiya nyaya sanhita, 2023", "bharatiya nyaya sanhita", "bns"],
        "areas": ["criminal"],
        "note": "Replaced the Indian Penal Code from 1 July 2024. Relevant only if a matter "
                "may involve cheating or fraud – a lawyer should advise on this.",
        "source": "https://www.indiacode.nic.in",
    },
    {
        "name": "Information Technology Act, 2000",
        "aliases": ["information technology act, 2000", "it act, 2000", "it act 2000"],
        "areas": ["cyber", "consumer"],
        "note": "Central law on electronic records and cyber offences. Electronic records such "
                "as emails and messages can be used as evidence.",
        "source": "https://www.indiacode.nic.in",
    },
]

# Laws that commonly appear in model outputs but have been replaced.
REPLACED_LAWS = {
    "payment of wages act": "Replaced by the Code on Wages, 2019 (in force from 21 Nov 2025).",
    "minimum wages act": "Replaced by the Code on Wages, 2019 (in force from 21 Nov 2025).",
    "indian penal code": "Replaced by the Bharatiya Nyaya Sanhita, 2023 (from 1 Jul 2024).",
    "code of criminal procedure": "Replaced by the Bharatiya Nagarik Suraksha Sanhita, 2023 "
                                  "(from 1 Jul 2024).",
    "indian evidence act": "Replaced by the Bharatiya Sakshya Adhiniyam, 2023 (from 1 Jul 2024).",
    "consumer protection act, 1986": "Replaced by the Consumer Protection Act, 2019.",
    "consumer protection act 1986": "Replaced by the Consumer Protection Act, 2019.",
}

OFFICIAL_RESOURCES = [
    {"name": "India Code (official repository of central and state laws)",
     "url": "https://www.indiacode.nic.in", "areas": ["general"]},
    {"name": "National Consumer Helpline – call 1915 or file online",
     "url": "https://consumerhelpline.gov.in", "areas": ["consumer"]},
    {"name": "e-Daakhil – online filing of consumer complaints with Consumer Commissions",
     "url": "https://edaakhil.nic.in", "areas": ["consumer"]},
    {"name": "Ministry of Labour & Employment (find your state Labour Department)",
     "url": "https://labour.gov.in", "areas": ["employment"]},
    {"name": "NALSA – free legal aid; national legal aid helpline 15100",
     "url": "https://nalsa.gov.in", "areas": ["general", "tenancy", "employment", "consumer"]},
    {"name": "National Cyber Crime Reporting Portal – helpline 1930 for online financial fraud",
     "url": "https://cybercrime.gov.in", "areas": ["cyber"]},
    {"name": "RBI Complaint Management System (banking / payment complaints)",
     "url": "https://cms.rbi.org.in", "areas": ["banking"]},
]

ISSUE_AREAS = {
    "tenancy": "Rent & Tenancy",
    "employment": "Salary & Employment",
    "consumer": "Consumer & Online Shopping",
    "cyber": "Cyber Fraud",
    "banking": "Banking & Payments",
    "property": "Property",
    "family": "Family",
    "criminal": "Criminal",
    "general": "Other / General",
}


def laws_for_area(area: str) -> list[dict]:
    return [l for l in VERIFIED_LAWS if area in l["areas"] or "general" in l["areas"]]


def resources_for_area(area: str) -> list[dict]:
    return [r for r in OFFICIAL_RESOURCES if area in r["areas"] or "general" in r["areas"]]


def allowlist_prompt_block(area: str) -> str:
    """Text injected into prompts so the model can only name vetted laws."""
    laws = laws_for_area(area)
    res = resources_for_area(area)
    lines = ["VERIFIED REFERENCE LIST (the ONLY laws/resources you may name):"]
    for l in laws:
        lines.append(f"- LAW: {l['name']} — {l['note']}")
    for r in res:
        lines.append(f"- RESOURCE: {r['name']} ({r['url']})")
    return "\n".join(lines)
