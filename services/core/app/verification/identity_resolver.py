from datetime import date
from typing import Optional
from dataclasses import dataclass
from rapidfuzz import fuzz

@dataclass
class CorroborationResult:
    score: float
    details: dict[str, str]

@dataclass
class IdentityRecord:
    source: str
    name: str
    dob: Optional[date]
    gender: Optional[str]
    father_name: Optional[str]
    mother_name: Optional[str]
    district: Optional[str]
    additional: Optional[dict] = None

@dataclass
class NameMatchResult:
    name_a: str
    name_b: str
    normalized_a: str
    normalized_b: str
    phonetic_a: str
    phonetic_b: str
    raw_similarity: float
    phonetic_similarity: float
    combined_score: float
    explanation: str

@dataclass
class IdentityResolution:
    overall_score: float
    decision: str
    name_comparisons: list[NameMatchResult]
    corroboration: CorroborationResult
    explanation: str
    details: dict

class IndicIdentityResolver:
    """Indic-aware identity resolution with explainable scoring."""
    
    AUTO_VERIFY_THRESHOLD = 0.92
    PROVISIONAL_THRESHOLD = 0.75
    
    def resolve(self, source_records: list[IdentityRecord]) -> IdentityResolution:
        if len(source_records) < 2:
            return IdentityResolution(
                overall_score=1.0,
                decision="AUTO_VERIFY",
                name_comparisons=[],
                corroboration=CorroborationResult(0.0, {}),
                explanation="Only one source record, nothing to compare.",
                details={}
            )
            
        base = source_records[0]
        comparisons = []
        overall_score = 0.0
        
        for record in source_records[1:]:
            comp = self.compare_names(base.name, record.name)
            comparisons.append(comp)
            
        avg_name_score = sum(c.combined_score for c in comparisons) / len(comparisons)
        corroboration = self._corroborate(source_records)
        final_score = min(1.0, avg_name_score + corroboration.score)
        
        decision, desc = self._decide(final_score)
        explanation = self._explain(comparisons[0], corroboration) if comparisons else "No comparisons made."
        
        return IdentityResolution(
            overall_score=final_score,
            decision=decision,
            name_comparisons=comparisons,
            corroboration=corroboration,
            explanation=f"{desc} {explanation}",
            details={"avg_name_score": avg_name_score, "corroboration_score": corroboration.score}
        )
    
    def compare_names(self, name_a: str, name_b: str) -> NameMatchResult:
        norm_a = self._normalize(name_a)
        norm_b = self._normalize(name_b)
        
        phon_a = self._phonetic_key(norm_a)
        phon_b = self._phonetic_key(norm_b)
        
        raw_sim = self._compute_similarity(norm_a, norm_b)
        phon_sim = self._compute_similarity(phon_a, phon_b)
        
        combined_score = (raw_sim * 0.4) + (phon_sim * 0.6)
        
        return NameMatchResult(
            name_a=name_a,
            name_b=name_b,
            normalized_a=norm_a,
            normalized_b=norm_b,
            phonetic_a=phon_a,
            phonetic_b=phon_b,
            raw_similarity=raw_sim,
            phonetic_similarity=phon_sim,
            combined_score=combined_score,
            explanation=f"Raw sim: {raw_sim:.2f}, Phonetic sim: {phon_sim:.2f}"
        )
    
    def _normalize(self, name: str) -> str:
        if not name: return ""
        name = name.lower().strip()
        remove_words = ["shri", "smt", "sri", "kumari", "kumar", "s/o", "d/o", "w/o", "c/o", "son of", "daughter of"]
        for word in remove_words:
            name = name.replace(word, "")
        return " ".join(name.split())
    
    def _transliterate(self, name: str) -> str:
        return name
    
    def _phonetic_key(self, name: str) -> str:
        rules = [
            ("v", "w"), ("sh", "s"), ("ph", "f"), ("th", "t"), 
            ("dh", "d"), ("bh", "b"), ("gh", "g"), ("kh", "k"),
            ("ch", "c"), ("ee", "i"), ("oo", "u"), ("aa", "a")
        ]
        res = name
        for old, new in rules:
            res = res.replace(old, new)
        if res.endswith("h"):
            res = res[:-1]
        
        # Deduplicate consecutive characters
        dedup = []
        for char in res:
            if not dedup or dedup[-1] != char:
                dedup.append(char)
        return "".join(dedup)
    
    def _align_tokens(self, tokens_a: list[str], tokens_b: list[str]) -> list[tuple]:
        return []
    
    def _compute_similarity(self, name_a: str, name_b: str) -> float:
        return fuzz.token_set_ratio(name_a, name_b) / 100.0
    
    def _corroborate(self, records: list[IdentityRecord]) -> CorroborationResult:
        if len(records) < 2: return CorroborationResult(0.0, {})
        base = records[0]
        score = 0.0
        details = {}
        for record in records[1:]:
            if base.dob and record.dob and base.dob == record.dob:
                score += 0.15
                details["dob"] = "Match"
            if base.gender and record.gender and base.gender.lower() == record.gender.lower():
                score += 0.05
                details["gender"] = "Match"
            if base.father_name and record.father_name:
                sim = fuzz.token_set_ratio(base.father_name.lower(), record.father_name.lower()) / 100.0
                if sim > 0.8:
                    score += 0.10
                    details["father_name"] = f"Match ({sim:.2f})"
            if base.district and record.district and base.district.lower() == record.district.lower():
                score += 0.05
                details["district"] = "Match"
        return CorroborationResult(min(0.35, score), details)
    
    def _decide(self, final_score: float) -> tuple[str, str]:
        if final_score >= self.AUTO_VERIFY_THRESHOLD:
            return "AUTO_VERIFY", "High confidence match."
        elif final_score >= self.PROVISIONAL_THRESHOLD:
            return "PROVISIONAL", "Borderline match, requires review."
        return "MANUAL_REVIEW", "Low confidence match, requires manual review."
    
    def _explain(self, comparison: NameMatchResult, corroboration: CorroborationResult) -> str:
        exp = [f"Name match score: {comparison.combined_score:.2f}."]
        for k, v in corroboration.details.items():
            exp.append(f"{k.capitalize()} {v}.")
        return " ".join(exp)
