import yaml
from pathlib import Path
from app.shared.types import CanonicalState

class StateMapper:
    def __init__(self, yaml_path: str):
        self.mapping = self._load_mapping(yaml_path)

    def _load_mapping(self, yaml_path: str) -> dict[str, CanonicalState]:
        path = Path(yaml_path)
        if not path.exists():
            return {}
            
        with open(path, "r") as f:
            data = yaml.safe_load(f)
            
        result = {}
        for k, v in data.get("states", {}).items():
            try:
                result[k] = CanonicalState(v)
            except ValueError:
                pass
        return result

    def map_state(self, external_state: str) -> CanonicalState:
        return self.mapping.get(external_state, CanonicalState.DRAFT)
