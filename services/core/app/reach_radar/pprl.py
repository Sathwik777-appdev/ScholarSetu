"""Privacy-Preserving Record Linkage using Bloom filter encoding.

Method:
1. Each record is encoded into a Bloom filter using character bigrams of name + DOB + district
2. A shared HMAC key ensures consistent encoding across data sources
3. Only Bloom filter encodings (not raw PII) are compared
4. Dice similarity coefficient determines matches
5. Unmatched enrolled ST students = potential unreached beneficiaries
"""
import hashlib
import hmac
import re
from typing import List, Tuple

class BloomFilterEncoder:
    """Encode identity records into Bloom filters for PPRL."""
    
    def __init__(self, filter_size: int = 1024, num_hash_functions: int = 20, secret_key: bytes = b"scholarsetu-pprl-key"):
        self.filter_size = filter_size
        self.num_hash_functions = num_hash_functions
        self.secret_key = secret_key
    
    def encode(self, name: str, dob: str, district: str) -> list[int]:
        """Encode a record into a Bloom filter.
        1. Normalize inputs
        2. Extract character bigrams
        3. Hash each bigram with HMAC
        4. Set bits in Bloom filter
        """
        bloom_filter = [0] * self.filter_size
        
        normalized_str = f"{name.lower().strip()}|{dob.strip()}|{district.lower().strip()}"
        normalized_str = re.sub(r'[^a-z0-9|]', '', normalized_str)
        
        bigrams = self._get_bigrams(normalized_str)
        
        for bigram in bigrams:
            for i in range(self.num_hash_functions):
                pos = self._hash_bigram(bigram, i)
                bloom_filter[pos] = 1
                
        return bloom_filter
    
    def _get_bigrams(self, text: str) -> list[str]:
        """Extract character bigrams from text."""
        if len(text) < 2:
            return [text]
        return [text[i:i+2] for i in range(len(text)-1)]
    
    def _hash_bigram(self, bigram: str, seed: int) -> int:
        """Hash a bigram to a bit position using HMAC."""
        # Mix the seed into the key or data
        data = f"{bigram}{seed}".encode('utf-8')
        h = hmac.new(self.secret_key, data, hashlib.sha256).digest()
        # Convert first 4 bytes to int and take modulo filter_size
        val = int.from_bytes(h[:4], byteorder='big')
        return val % self.filter_size

class PPRLMatch:
    def __init__(self, index_a: int, index_b: int, score: float):
        self.index_a = index_a
        self.index_b = index_b
        self.score = score

class PPRLMatcher:
    """Match encoded records using Dice similarity."""
    
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
    
    def dice_similarity(self, bloom_a: list[int], bloom_b: list[int]) -> float:
        """Compute Dice coefficient between two Bloom filters."""
        if len(bloom_a) != len(bloom_b):
            raise ValueError("Bloom filters must be of the same size")
            
        intersection = sum(a & b for a, b in zip(bloom_a, bloom_b))
        sum_a = sum(bloom_a)
        sum_b = sum(bloom_b)
        
        if sum_a + sum_b == 0:
            return 0.0
            
        return (2.0 * intersection) / (sum_a + sum_b)
    
    def find_matches(self, source_encodings: list[list[int]], target_encodings: list[list[int]]) -> list[PPRLMatch]:
        """Find matches between two sets of encoded records."""
        matches = []
        for i, source in enumerate(source_encodings):
            best_score = 0
            best_match = -1
            
            for j, target in enumerate(target_encodings):
                score = self.dice_similarity(source, target)
                if score > best_score:
                    best_score = score
                    best_match = j
                    
            if best_score >= self.threshold:
                matches.append(PPRLMatch(i, best_match, best_score))
                
        return matches
    
    def find_unmatched(self, enrolled_encodings: list[list[int]], scholarship_encodings: list[list[int]]) -> list[int]:
        """Find enrolled records that don't match any scholarship record.
        These are potential unreached beneficiaries."""
        matches = self.find_matches(enrolled_encodings, scholarship_encodings)
        matched_enrolled_indices = {m.index_a for m in matches}
        
        unmatched = []
        for i in range(len(enrolled_encodings)):
            if i not in matched_enrolled_indices:
                unmatched.append(i)
                
        return unmatched
