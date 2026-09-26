"""RAG (Retrieval Augmented Generation) for scheme guidelines."""
from app.shared.types import SchemeType
from .schemas import GuidelineResult

class GuidelineRAG:
    """Search scheme guidelines using embeddings + pgvector."""
    
    # For prototype, use a simple keyword-based search
    # In production, use multilingual-e5-small embeddings + pgvector
    
    GUIDELINES = {
        SchemeType.PRE_MATRIC: [
            {
                "section": "Eligibility",
                "content": "The Pre-Matric Scholarship is for ST students studying in Classes 9 and 10. The family annual income should not exceed ₹2,50,000 from all sources. The student must be enrolled in a Government school or in a school recognized by the Government/local body.",
                "source": "Pre-Matric Scholarship Guidelines, MoTA"
            },
            {
                "section": "Scholarship Amount",
                "content": "Day scholars: ₹3,500/year for Class 9, ₹3,500/year for Class 10. Hostellers: ₹7,000/year for Class 9, ₹7,000/year for Class 10. Additional ad-hoc grant for books and stationery.",
                "source": "Pre-Matric Scholarship Guidelines, MoTA"
            },
        ],
        SchemeType.POST_MATRIC: [
            {
                "section": "Eligibility",
                "content": "Post-Matric Scholarship is for ST students studying at post-matriculation or post-secondary stage. Family income should not exceed ₹2,50,000 per annum. Available for courses from Class 11 up to Ph.D level in recognized institutions.",
                "source": "Post-Matric Scholarship Guidelines, MoTA"
            },
            {
                "section": "Scholarship Amount",
                "content": "Varies by course group (I to IV). Group I (degree & PG): Maintenance allowance of ₹1,200/month (hostellers) or ₹550/month (day scholars) plus compulsory fees.",
                "source": "Post-Matric Scholarship Guidelines, MoTA"
            },
        ],
        SchemeType.TOP_CLASS: [
            {
                "section": "Eligibility",
                "content": "Top Class Education Scheme supports ST students admitted to notified premier institutions (IITs, IIMs, NITs, AIIMS, NLUs, etc.). Family income should not exceed ₹6,00,000 per annum.",
                "source": "Top Class Education Guidelines, MoTA"
            },
            {
                "section": "Benefits",
                "content": "Full tuition fee and non-refundable fees. Living expenses up to ₹2,20,000/year. Book grant, computer/laptop allowance (one-time).",
                "source": "Top Class Education Guidelines, MoTA"
            },
        ],
        SchemeType.NFST: [
            {
                "section": "Eligibility",
                "content": "National Fellowship for ST (NFST) is for ST students pursuing M.Phil/Ph.D. Must have qualified NET/JRF conducted by UGC-NTA. Total 750 fellowships per year.",
                "source": "NFST Guidelines, MoTA"
            },
            {
                "section": "Fellowship Amount",
                "content": "JRF: ₹31,000/month for initial 2 years. SRF: ₹35,000/month for remaining tenure. Plus HRA as per norms, contingency grant, and escort/reader allowance for PwD.",
                "source": "NFST Guidelines, MoTA"
            },
        ],
        SchemeType.NOS: [
            {
                "section": "Eligibility",
                "content": "National Overseas Scholarship for ST students going abroad for Master's, Ph.D, or Post-doctoral research. Family income should not exceed ₹6,00,000 per annum. Age limit: 35 years.",
                "source": "NOS Guidelines, MoTA"
            },
            {
                "section": "Benefits",
                "content": "Full tuition fees and other institutional charges. Annual maintenance allowance. Contingency and equipment allowance. Travel cost (economy class).",
                "source": "NOS Guidelines, MoTA"
            },
        ],
    }
    
    async def search(self, query: str, scheme: SchemeType | None = None) -> list[GuidelineResult]:
        """Search guidelines using keyword matching (prototype) or embeddings (production)."""
        results = []
        query_lower = query.lower()
        
        schemes_to_search = [scheme] if scheme else list(self.GUIDELINES.keys())
        
        for s in schemes_to_search:
            sections = self.GUIDELINES.get(s, [])
            for section in sections:
                if query_lower in section["content"].lower() or query_lower in section["section"].lower():
                    results.append(GuidelineResult(
                        section=section["section"],
                        content=section["content"],
                        source=section["source"],
                        relevance_score=0.9
                    ))
        
        return results
    
    async def get_section(self, scheme: SchemeType, section: str) -> GuidelineResult | None:
        """Get a specific section of guidelines."""
        sections = self.GUIDELINES.get(scheme, [])
        for sec in sections:
            if sec["section"].lower() == section.lower():
                return GuidelineResult(
                    section=sec["section"],
                    content=sec["content"],
                    source=sec["source"],
                    relevance_score=1.0
                )
        return None
