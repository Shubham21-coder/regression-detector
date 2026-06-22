from pydantic import BaseModel
from typing import List, Dict
import yaml, os


class FewShotExample(BaseModel):
    input: str
    output: str


class PromptConfig(BaseModel):
    version_id: str
    timestamp: str
    system_prompt: str
    few_shot_examples: List[FewShotExample]

    @classmethod
    def from_yaml(cls, path: str) -> "PromptConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def build_messages(self, user_text: str) -> List[Dict]:
        messages = [{"role": "system", "content": self.system_prompt}]
        for ex in self.few_shot_examples:
            messages.append({"role": "user", "content": ex.input})
            messages.append({"role": "assistant", "content": ex.output})
        messages.append({"role": "user", "content": user_text})
        return messages
