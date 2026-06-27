"""
Hardcoded text chunks for Consumer Protection Act 2019 and IT Act 2000.
Used as a fallback when PDFs cannot be downloaded from government websites.

These are condensed summaries of the key provisions, not the full act text.
Good enough for RAG retrieval of the most commonly queried sections.
"""

CPA_2019_CHUNKS = [
    {
        "text": (
            "Consumer Protection Act 2019 (Act No. 35 of 2019). "
            "The Consumer Protection Act 2019 replaced the Consumer Protection Act 1986. "
            "It applies to all goods and services, including e-commerce transactions. "
            "Key features: Central Consumer Protection Authority (CCPA) established to promote, "
            "protect and enforce consumer rights. Product liability provisions introduced. "
            "Unfair trade practices and misleading advertisements addressed. "
            "E-commerce and direct selling regulated. Mediation as alternate dispute resolution."
        ),
        "metadata": {
            "name": "Consumer Protection Act 2019",
            "short_name": "cpa_2019",
            "category": "consumer",
            "year": 2019,
            "source_url": "https://consumeraffairs.gov.in",
            "chunk_index": 0,
            "char_start": 0,
        },
    },
    {
        "text": (
            "Consumer Protection Act 2019 - Consumer Rights (Section 2). "
            "Every consumer has the right to: be protected against hazardous goods and services; "
            "be informed about quality, quantity, potency, purity, standard and price; "
            "be assured access to a variety of goods and services at competitive prices; "
            "be heard and assured that consumers' interests will receive due consideration; "
            "seek redressal against unfair trade practices; "
            "consumer awareness and education."
        ),
        "metadata": {
            "name": "Consumer Protection Act 2019",
            "short_name": "cpa_2019",
            "category": "consumer",
            "year": 2019,
            "source_url": "https://consumeraffairs.gov.in",
            "chunk_index": 1,
            "char_start": 800,
        },
    },
    {
        "text": (
            "Consumer Protection Act 2019 - District Consumer Disputes Redressal Commission. "
            "Section 34: Jurisdiction - A complaint shall be instituted in a District Commission "
            "within whose local limits the opposite party resides or carries on business, "
            "or the complaint is filed where the complainant resides. "
            "Pecuniary jurisdiction: Up to Rs 1 crore. "
            "State Commission: Rs 1 crore to Rs 10 crore. "
            "National Commission (NCDRC): Above Rs 10 crore. "
            "No fee for complaints up to Rs 5 lakh."
        ),
        "metadata": {
            "name": "Consumer Protection Act 2019",
            "short_name": "cpa_2019",
            "category": "consumer",
            "year": 2019,
            "source_url": "https://consumeraffairs.gov.in",
            "chunk_index": 2,
            "char_start": 1600,
        },
    },
    {
        "text": (
            "Consumer Protection Act 2019 - Product Liability (Chapter VI). "
            "Section 82: A product manufacturer shall be liable in a product liability action if "
            "the product contains a manufacturing defect, is defective in design, "
            "deviates from manufacturing specifications, or does not conform to express warranty. "
            "Section 83: A product seller shall be liable if product is defective, "
            "seller failed to exercise reasonable care, or seller made an express warranty. "
            "Section 84: A product service provider shall be liable for harm caused by "
            "deficient services."
        ),
        "metadata": {
            "name": "Consumer Protection Act 2019",
            "short_name": "cpa_2019",
            "category": "consumer",
            "year": 2019,
            "source_url": "https://consumeraffairs.gov.in",
            "chunk_index": 3,
            "char_start": 2400,
        },
    },
    {
        "text": (
            "Consumer Protection Act 2019 - Unfair Trade Practices and Misleading Advertisements. "
            "Section 2(47): Unfair trade practice means a trade practice for promoting sale, "
            "use or supply of any goods or for provision of any service which adopts any unfair "
            "method or unfair or deceptive practice. Includes: false representation of standard/quality; "
            "false offers of bargain price; offering prizes with no intention to provide them; "
            "pyramid schemes. "
            "Section 21: CCPA may issue directions to discontinue misleading advertisements "
            "and impose penalty up to Rs 10 lakh."
        ),
        "metadata": {
            "name": "Consumer Protection Act 2019",
            "short_name": "cpa_2019",
            "category": "consumer",
            "year": 2019,
            "source_url": "https://consumeraffairs.gov.in",
            "chunk_index": 4,
            "char_start": 3200,
        },
    },
    {
        "text": (
            "Consumer Protection Act 2019 - E-commerce Provisions. "
            "E-commerce entities must provide information on return, refund, exchange, "
            "warranty, guarantee, delivery, mode of payment, grievance redressal mechanism. "
            "They must not impose cancellation charges unless similar charges are also borne by them. "
            "Sellers on marketplace e-commerce platforms must have a grievance officer. "
            "Consumer Helpline: 1915. National Consumer Helpline: 1800-11-4000."
        ),
        "metadata": {
            "name": "Consumer Protection Act 2019",
            "short_name": "cpa_2019",
            "category": "consumer",
            "year": 2019,
            "source_url": "https://consumeraffairs.gov.in",
            "chunk_index": 5,
            "char_start": 4000,
        },
    },
    {
        "text": (
            "Information Technology Act 2000 (Act No. 21 of 2000) - Overview. "
            "The Information Technology Act 2000 provides legal recognition for transactions "
            "carried out by means of electronic data interchange and other means of electronic "
            "communication, commonly referred to as electronic commerce. "
            "Applies to: electronic contracts, digital signatures, cyber offences, "
            "electronic governance, data protection. "
            "Does NOT apply to: negotiable instruments, power-of-attorney, trust, will, "
            "immovable property transactions."
        ),
        "metadata": {
            "name": "Information Technology Act 2000",
            "short_name": "it_act_2000",
            "category": "cyber",
            "year": 2000,
            "source_url": "https://www.meity.gov.in",
            "chunk_index": 0,
            "char_start": 0,
        },
    },
    {
        "text": (
            "Information Technology Act 2000 - Cyber Offences (Chapter XI). "
            "Section 43: Penalty for damage to computer/network - compensation up to Rs 1 crore. "
            "Section 66: Computer related offences - imprisonment up to 3 years or fine up to Rs 5 lakh. "
            "Section 66A (struck down by SC in 2015): Sending offensive messages. "
            "Section 66B: Receiving stolen computer resource - imprisonment up to 3 years. "
            "Section 66C: Identity theft - imprisonment up to 3 years, fine up to Rs 1 lakh. "
            "Section 66D: Cheating by personation - imprisonment up to 3 years, fine up to Rs 1 lakh."
        ),
        "metadata": {
            "name": "Information Technology Act 2000",
            "short_name": "it_act_2000",
            "category": "cyber",
            "year": 2000,
            "source_url": "https://www.meity.gov.in",
            "chunk_index": 1,
            "char_start": 800,
        },
    },
    {
        "text": (
            "Information Technology Act 2000 - More Cyber Offences. "
            "Section 66E: Violation of privacy - publishing private images without consent - "
            "imprisonment up to 3 years or fine up to Rs 2 lakh. "
            "Section 66F: Cyber terrorism - imprisonment which may extend to imprisonment for life. "
            "Section 67: Publishing obscene material in electronic form - "
            "imprisonment up to 3 years, fine up to Rs 5 lakh (first conviction). "
            "Section 67A: Publishing sexually explicit material - imprisonment up to 5 years. "
            "Section 67B: Child pornography - imprisonment up to 5 years (first conviction)."
        ),
        "metadata": {
            "name": "Information Technology Act 2000",
            "short_name": "it_act_2000",
            "category": "cyber",
            "year": 2000,
            "source_url": "https://www.meity.gov.in",
            "chunk_index": 2,
            "char_start": 1600,
        },
    },
    {
        "text": (
            "Information Technology Act 2000 - Intermediary Liability and Safe Harbour. "
            "Section 79: Exemption from liability of intermediary - An intermediary shall not be "
            "liable for any third party information, data or communication link made available "
            "by it, if it acts as a mere conduit, does not initiate transmission, "
            "does not select receiver, does not modify information, and observes due diligence. "
            "Intermediaries include: telecom service providers, network service providers, "
            "internet service providers, web hosting service providers, search engines, "
            "online payment sites, online auction sites, online marketplaces."
        ),
        "metadata": {
            "name": "Information Technology Act 2000",
            "short_name": "it_act_2000",
            "category": "cyber",
            "year": 2000,
            "source_url": "https://www.meity.gov.in",
            "chunk_index": 3,
            "char_start": 2400,
        },
    },
    {
        "text": (
            "Information Technology Act 2000 - Data Protection and Sensitive Personal Information. "
            "Section 43A: Compensation for failure to protect sensitive personal data - "
            "a body corporate possessing, dealing or handling sensitive personal data is liable "
            "to pay compensation if it is negligent in implementing reasonable security practices. "
            "IT (Amendment) Act 2008 introduced Section 66A (now struck down), 66B to 66F, "
            "and Section 69: Power to issue directions for interception, monitoring, decryption. "
            "Section 70: Protected systems - Government may declare any computer resource as protected. "
            "Penalty for unauthorized access: imprisonment up to 10 years."
        ),
        "metadata": {
            "name": "Information Technology Act 2000",
            "short_name": "it_act_2000",
            "category": "cyber",
            "year": 2000,
            "source_url": "https://www.meity.gov.in",
            "chunk_index": 4,
            "char_start": 3200,
        },
    },
]
