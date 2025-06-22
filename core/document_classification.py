from langchain_core.runnables import Runnable
from openai import OpenAI
import numpy as np
from typing import List, Dict, Any
from langchain.prompts import PromptTemplate
import tiktoken
from openai.types.chat import ChatCompletion


class RunnableGPTLogprobClassifier(Runnable):
    def __init__(self, label_descs: dict, model="gpt-4o-mini", max_prompt_chars=5500, max_pages=10):
        self.model = model
        self.labels_descriptions = label_descs
        self.labels = list(label_descs.keys())
        self.max_prompt_chars = max_prompt_chars
        self.max_pages = max_pages
        self.client = OpenAI()
        self.prompt_template = self.build_classification_prompt_template()
        self.input_tokens = 0  # Initialize input tokens count
        self.output_tokens = 0  # Initialize output tokens count

    def build_classification_prompt_template(self) -> PromptTemplate:
        """
        Build a PromptTemplate for document classification.

        Args:
            label_descs (dict): A dictionary where keys are label names (single words)
                                and values are their descriptions.

        Returns:
            PromptTemplate: LangChain prompt template ready for formatting.
        """
        # Format label descriptions
        label_lines = "\n".join(
            f"- {label}: {desc}" for label, desc in self.labels_descriptions.items()
        )
        label_list = ", ".join(self.labels)

        # Construct template string (not using f-string for {content})
        template = (
            "You are a document classification system. Your task is to classify a business document "
            "into one of the following types:\n\n"
            f"{label_lines}\n\n"
            "Document content:\n"
            "{content}\n\n"
            f"Respond with only one of the following labels: {label_list}."
        )

        return PromptTemplate.from_template(template)

    def _softmax_from_logprobs(self, label_logprobs: Dict[str, float]) -> Dict[str, float]:
        logits = np.array(list(label_logprobs.values()))
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()
        return dict(zip(label_logprobs.keys(), map(float, probs)))

    def invoke(self, input: List[Dict[str, Any]]) -> Dict[str, Any]:
        # input: list of page dicts (with "text" field)
        if self.max_pages is not None:
            input = input[:self.max_pages]
        sample_text = "\n\n".join(p["text"] for p in input)
        # Truncate to max characters
        if self.max_prompt_chars is not None:
            sample_text = sample_text[:self.max_prompt_chars]

        prompt = self.prompt_template.format(
            content=sample_text
        )

        response: ChatCompletion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1,
            logprobs=True,
            temperature=0,
            top_logprobs=10
        )
        try:
            logprobs_data = response.choices[0].logprobs.content[0].top_logprobs
        except (AttributeError, IndexError):
            raise ValueError("Unexpected response format from OpenAI API. Ensure the model supports logprobs.\n Response: " + str(response))
        try:
            self.input_tokens += response.usage.prompt_tokens
            self.output_tokens += response.usage.completion_tokens
        except AttributeError:
            print("Warning: Usage information not available in the response. Make sure your OpenAI client is configured correctly.")
            pass

        label_logprobs = {}
        for entry in logprobs_data:
            token = entry.token.strip()
            if token in self.labels:
                label_logprobs[token] = entry.logprob

        if not label_logprobs:
            raise ValueError("No valid labels found in logprobs. Ensure the model is correctly configured.")

        probs = self._softmax_from_logprobs(label_logprobs)
        top_label = max(probs, key=probs.get)

        return {
            "type": top_label,
            "confidence": probs[top_label],
            # "probs": probs ## Uncomment if you want to return all probabilities
        }
