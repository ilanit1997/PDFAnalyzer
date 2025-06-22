import json
import os
from uuid import uuid4
from core.document_pipeline import DocumentPipelineManager

if __name__ == "__main__":
    input_folder = r"C:\Users\ilanit\PycharmProjects\factify\documents-extra"
    output_folder = r"C:\Users\ilanit\PycharmProjects\factify\output-extra"
    os.makedirs(output_folder, exist_ok=True)

    # 👇 Load existing results if they exist
    all_results_path = os.path.join(output_folder, "all_results.json")
    if os.path.exists(all_results_path):
        with open(all_results_path, "r", encoding="utf-8") as f:
            all_results = json.load(f)
    else:
        all_results = {}
    pipeline = DocumentPipelineManager(max_pages_classification=3)

    for doc_type_folder in os.listdir(input_folder):
        curr_input_folder = os.path.join(input_folder, doc_type_folder)
        curr_output_folder = os.path.join(output_folder, doc_type_folder)
        os.makedirs(curr_output_folder, exist_ok=True)
        for file_name in os.listdir(curr_input_folder):
            print(f"Processing {file_name}")
            file_name_clean = file_name.split(".")[0]
            output_file = os.path.join(curr_output_folder, f"{file_name_clean}.json")
            key = f"{doc_type_folder}_{file_name_clean}"

            # 👇 Skip if file was processed already
            if os.path.exists(output_file) or key in all_results:
                print(f"Output for {key} already exists, skipping.")
                continue

            pages = pipeline.load_document(os.path.join(curr_input_folder, file_name))
            classification_result = pipeline.classify(pages)
            metadata_result = pipeline.extract_metadata(pages, classification_result["type"])

            doc_id = str(uuid4())
            input_tokens = pipeline.total_input_tokens
            output_tokens = pipeline.total_output_tokens
            total_cost = pipeline.calculate_costs()

            print(f"#Input tokens: {input_tokens}, #Output tokens: {output_tokens} -> Total cost: ${total_cost:.6f}")

            output = {
                "id": doc_id,
                "classification": classification_result,
                "metadata": metadata_result.model_dump() if hasattr(metadata_result, "model_dump") else metadata_result,
            }

            all_results[key] = output

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=4)

            print(f"Classification: {classification_result}")
            print(f"Metadata: {metadata_result}\n")

            # 👇 Save cumulative results after each doc
            with open(all_results_path, "w", encoding="utf-8") as f:
                json.dump(all_results, f, ensure_ascii=False, indent=4)
