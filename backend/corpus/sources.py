"""
Legal source definitions for JustiBot corpus ingestion.
Contains official Indian legal document URLs and helpline data.

URL Selection Rationale:
- www.mha.gov.in (with www): serves PDFs directly; mha.gov.in (no www) redirects to Hindi IDN
- egazette.gov.in: official gazette, reliable for new criminal laws
- cic.gov.in: Central Information Commission — serves RTI Act PDF without restriction
- consumeraffairs.nic.in: SSL cert issue but our downloader retries with verify=False
- meity.gov.in: Ministry of Electronics, serves IT Act PDF directly
"""

LEGAL_SOURCES = [
    {
        "name": "Bharatiya Nyaya Sanhita 2023",
        "short_name": "bns_2023",
        # www.mha.gov.in serves this directly; bare mha.gov.in redirects to Hindi IDN
        "url": "https://www.mha.gov.in/sites/default/files/250883_english_01042024.pdf",
        "source_type": "pdf",
        "category": "criminal",
        "year": 2023,
    },
    {
        "name": "Bharatiya Nagarik Suraksha Sanhita 2023",
        "short_name": "bnss_2023",
        # Official eGazette — gazette notification number 250884
        "url": "https://egazette.gov.in/WriteReadData/2023/250884.pdf",
        "source_type": "pdf",
        "category": "procedural",
        "year": 2023,
    },
    {
        "name": "Constitution of India",
        "short_name": "constitution",
        "url": "https://cdnbbsr.s3waas.gov.in/s380537a945c7aaa788ccfcdf1b99b5d8f/uploads/2023/05/2023050195.pdf",
        "source_type": "pdf",
        "category": "constitutional",
        "year": 2023,
    },
    {
        "name": "RTI Act 2005",
        "short_name": "rti_2005",
        # Central Information Commission — reliable, no bot-blocking
        "url": "https://cic.gov.in/sites/default/files/RTI-Act_English.pdf",
        "source_type": "pdf",
        "category": "civil",
        "year": 2005,
    },
    {
        "name": "Consumer Protection Act 2019",
        "short_name": "cpa_2019",
        # India Code HTML page — renders full act text, no bot-blocking
        "url": "https://www.indiacode.nic.in/bitstream/123456789/15256/1/a2019-35.pdf",
        "source_type": "pdf",
        "category": "consumer",
        "year": 2019,
    },
    {
        "name": "Information Technology Act 2000",
        "short_name": "it_act_2000",
        # India Code PDF — direct bitstream download, no bot-blocking
        "url": "https://www.indiacode.nic.in/bitstream/123456789/1999/3/A2000-21.pdf",
        "source_type": "pdf",
        "category": "cyber",
        "year": 2000,
    },
    {
        "name": "Cyber Crime Reporting",
        "short_name": "cybercrime_portal",
        "url": "https://www.cybercrime.gov.in/Webform/Crime_AboutUs.aspx",
        "source_type": "html",
        "category": "cyber",
        "year": 2024,
    },
]

LEGAL_HELPLINES = [
    {
        "name": "National Cyber Crime Helpline",
        "number": "1930",
        "url": "https://cybercrime.gov.in",
    },
    {
        "name": "Police Emergency",
        "number": "100",
        "url": None,
    },
    {
        "name": "Women Helpline",
        "number": "1091",
        "url": None,
    },
    {
        "name": "Consumer Helpline",
        "number": "1915",
        "url": "https://consumerhelpline.gov.in",
    },
    {
        "name": "National Legal Services Authority",
        "number": "15100",
        "url": "https://nalsa.gov.in",
    },
    {
        "name": "Senior Citizen Helpline",
        "number": "14567",
        "url": None,
    },
]
