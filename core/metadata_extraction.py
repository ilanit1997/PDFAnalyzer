from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser

class LineItem(BaseModel):
    description: str
    quantity: Optional[Union[int, float]]
    amount: Optional[Union[int, float]]

class InvoiceMetadata(BaseModel):
    vendor: Optional[str]
    amount: Optional[Union[int, float]]
    due_date: Optional[str]
    line_items: Optional[List[LineItem]]

class ContractMetadata(BaseModel):
    parties: Optional[List[str]]
    effective_date: Optional[str]
    termination_date: Optional[str]
    key_terms: Optional[List[str]]

class KeyMetric(BaseModel):
    name: str
    value: Optional[str]  # Keep as str to support values like "$1.2B", "15%", "N/A"

class ReportMetadata(BaseModel):
    reporting_period: Optional[str]
    key_metrics: Optional[List[KeyMetric]]
    executive_summary: Optional[str]

class OtherMetadata(BaseModel):
    summary: Optional[str]

def get_invoice_prompt():
    parser = PydanticOutputParser(pydantic_object=InvoiceMetadata)
    template = PromptTemplate(
        template="""
You are an intelligent data extractor for business invoices.

Extract the following fields:
- vendor: name of the vendor or company issuing the invoice
- amount: total amount in the invoice
- due_date: in YYYY-MM-DD format (e.g., 2024-03-25). Only include if explicitly mentioned and applicable.
- line_items: A list of items, each containing a description, quantity, and total amount of line item, if available. Include all items explicitly mentioned in the text, even if some fields are missing or have a value of 0 (e.g., amount, quantity). 

Do not infer the actual values, just extract what is present in the text.

{format_instructions}

Invoice text:
{content}
""",
        input_variables=["content"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    return template, parser


def get_contract_prompt():
    parser = PydanticOutputParser(pydantic_object=ContractMetadata)
    template = PromptTemplate(
        template="""
You are a document intelligence system focused on contracts.

Extract the following metadata:
- parties involved
- effective date: in YYYY-MM-DD format (e.g., 2024-03-25)
- termination date: in YYYY-MM-DD format (e.g., 2024-03-25)
- key terms (as a list of strings)

{format_instructions}

Contract content:
{content}
""",
        input_variables=["content"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    return template, parser


def get_report_prompt():
    parser = PydanticOutputParser(pydantic_object=ReportMetadata)
    template = PromptTemplate(
        template="""
You are an AI system extracting key information from business earnings reports.

Extract the following fields:
- reporting period
- key metrics
- executive summary (a short paragraph)

{format_instructions}

Report content:
{content}
""",
        input_variables=["content"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    return template, parser

def get_other_prompt():
    parser = PydanticOutputParser(pydantic_object=OtherMetadata)
    template = PromptTemplate(
        template="""
You are an AI system summarizing general business documents that do not fit a specific category.

Extract the following fields:
- summary: a concise 3-5 sentence overview of the document

{format_instructions}

Document content:
{content}
""",
        input_variables=["content"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    return template, parser



class RunnableMetadataExtractor(Runnable):
    def __init__(self, doc_type: str, model: str = "gpt-4o-mini",
                 max_chars: Union[int, None] = None,
                 max_pages: Union[int, None] = None):
        self.doc_type = doc_type
        self.max_prompt_chars = max_chars
        self.max_pages = max_pages
        self.model = model
        self.llm = ChatOpenAI(model_name=model, temperature=0.0, max_tokens=1000)
        # Get prompt + parser at initialization
        self.prompt, self.parser = self.get_prompt_and_parser_for_type(doc_type)
        self.input_tokens = 0
        self.output_tokens = 0

    def get_prompt_and_parser_for_type(self, doc_type: str):
        if doc_type == "Invoice":
            return get_invoice_prompt()
        elif doc_type == "Contract":
            return get_contract_prompt()
        elif doc_type in ["Earnings", "Report"]:
            return get_report_prompt()
        elif doc_type == "Other":
            return get_other_prompt()
        else:
            raise ValueError(f"Unsupported document type: {doc_type}")
    
    def invoke(self, pages: List[Dict[str, Any]]) -> Optional[BaseModel]:
        # Combine text from first 3 pages
        if self.max_pages is not None:
            pages = pages[:self.max_pages]
        content = "\n\n".join(p["text"] for p in pages)
        # Truncate to max characters
        if self.max_prompt_chars is not None:
            content = content[:self.max_prompt_chars]
        # Format prompt
        messages = [
            {"role": "system", "content": "You extract structured metadata from business documents parsed as text from PDF. Focus only on the information present in the text."}
            , {"role": "user", "content": self.prompt.format(content=content)}
        ]
        # Call LLM
        response = self.llm.invoke(messages)
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            self.input_tokens += response.usage_metadata['input_tokens']
            self.output_tokens += response.usage_metadata['output_tokens']
        # Parse response into structured metadata
        try:
            return self.parser.parse(response.content)
        except Exception as e:
            raise ValueError(f"Failed to parse metadata for {self.doc_type}: {e}") from e