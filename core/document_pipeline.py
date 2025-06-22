from core.document_classification import RunnableGPTLogprobClassifier
from core.metadata_extraction import RunnableMetadataExtractor
from typing import List
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import pdfplumber

class DocumentPipelineManager:
    def __init__(self, model_name: str = "gpt-4o-mini",
                 max_pages_classification: int = 10, max_pages_extraction: int = None):
        self.label_descriptions = {
            "Invoice": "A bill for goods or services, typically including vendor, amount, due date, and line items.",
            "Contract": "A legal agreement between parties, containing terms, dates, and responsibilities.",
            "Earnings": "A financial or business report summarizing revenue, profits, expenses, and other key metrics.",
            "Other": "Any other type of document that does not fit the above categories."
        }
        self.classifier = RunnableGPTLogprobClassifier(
            label_descs=self.label_descriptions,
            model=model_name,
            max_pages=max_pages_classification,
        )
        self.extractors = {
            doc_type: RunnableMetadataExtractor(doc_type=doc_type,
                                                model=model_name,
                                                max_pages=max_pages_extraction)
            for doc_type in self.label_descriptions.keys()
        }
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def load_document(self, path: str) -> List[dict]:
        pages = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages.append({
                    "page": i + 1,
                    "text": text,
                })

        return pages

    def calculate_costs(self, input_cost: float = 0.6, output_cost: float = 2.4) -> float:
        """
        Calculate the cost of an API call based on the number of input and output tokens.

        Args:
            input_tokens (int): Number of input tokens used.
            output_tokens (int): Number of output tokens generated.
            input_cost (float): Cost per input token (default for GPT-4o mini: $0.60 per 1M tokens).
            output_cost (float): Cost per output token (default for GPT-4o mini: $2.4 per 1M tokens).

        Returns:
            float: Total cost in USD.
        """
        return (self.total_input_tokens / 1000000 )* input_cost + (self.total_output_tokens / 1000000 ) * output_cost

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(0.5),
        retry=retry_if_exception_type(ValueError)
    )
    def classify(self, pages):
        output = self.classifier.invoke(pages)
        self.total_input_tokens += self.classifier.input_tokens
        self.total_output_tokens += self.classifier.output_tokens
        return output

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(0.5),
        retry=retry_if_exception_type(ValueError)
    )
    def extract_metadata(self, pages, doc_type: str):
        extractor = self.extractors.get(doc_type)
        self.total_input_tokens += self.extractors.get(doc_type).input_tokens
        self.total_output_tokens += self.extractors.get(doc_type).input_tokens
        if extractor is None:
            raise ValueError(f"Unsupported document type: {doc_type}")
        return extractor.invoke(pages)

    def get_supported_doc_types(self):
        return list(self.label_descriptions.keys())
