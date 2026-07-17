"""
Temporary debug script — runs the 11 misclassified queries through
the classifier with CLASSIFY-DEBUG logging active.
Run with:
  backend\venv\Scripts\python.exe backend\evaluation\debug_classify.py
"""

import asyncio
import sys
sys.path.insert(0, ".")

from backend.services.groq_service import GroqService
from backend.services.query_classifier_service import QueryClassifierService

# 11 misclassified cases from the first eval run
MISCLASSIFIED = [
    ("tc_002", "What punishment does the IT Act prescribe for hacking?",                              "LEGAL_COMPLEX"),
    ("tc_003", "What does Section 67 of the IT Act say about publishing obscene content online?",     "LEGAL_COMPLEX"),
    ("tc_004", "What is the maximum period a person can be detained in police custody under BNSS?",    "LEGAL_COMPLEX"),
    ("tc_005", "What is the offence of sedition under the BNS 2023?",                                 "LEGAL_COMPLEX"),
    ("tc_006", "What is the maximum period a person can be detained in police custody under BNSS?",    "LEGAL_COMPLEX"),
    ("tc_007", "What are the rights of an arrested person under BNSS?",                               "LEGAL_COMPLEX"),
    ("tc_009", "What fundamental rights does the Constitution give to Indian citizens?",               "LEGAL_COMPLEX"),
    ("tc_011", "What information is exempt from disclosure under the RTI Act?",                       "LEGAL_COMPLEX"),
    ("tc_015", "How is property distributed under Hindu succession law in India?",                    "LEGAL_COMPLEX"),
    ("tc_017", "What are the grounds for divorce under Indian family law?",                           "LEGAL_COMPLEX"),
]


async def main():
    groq_svc = GroqService()
    classifier = QueryClassifierService(groq_svc.client)

    print("=" * 70)
    print("CLASSIFIER DEBUG — misclassified cases")
    print("=" * 70)

    for tc_id, query, expected in MISCLASSIFIED:
        print(f"\n--- {tc_id} ---")
        result = await classifier.classify(query)
        status = "OK" if result["category"] == expected else "FAIL"
        print(f"  expected={expected:<14}  got={result['category']:<14}  [{status}]")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
