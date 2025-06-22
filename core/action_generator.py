from typing import List, Dict

def actions_for_invoice(metadata: Dict) -> List[Dict]:
    actions = []
    actions.append({
        "type": "talk_to_finance_team",
        "description": f"Discuss invoice from {metadata.get('vendor', 'unknown vendor')} with finance team.",
        "deadline": metadata["due_date"],
        "priority": "medium"
    })
    if metadata.get("due_date"):
        actions.append({
            "type": "payment_due",
            "description": f"Schedule payment of {metadata.get('amount')} to {metadata.get('vendor')}.",
            "deadline": metadata["due_date"],
            "priority": "high"
        })
    return actions

def actions_for_contract(metadata: Dict) -> List[Dict]:
    actions = []
    actions.append({
        "type": "print_contract",
        "description": f"Print contract with {', '.join(metadata.get('parties', []))}.",
        "priority": "low"
    })


    if metadata.get("termination_date"):
        actions.append({
            "type": "review_contract",
            "description": f"Review contract before termination with {', '.join(metadata.get('parties', []))}.",
            "deadline": metadata["termination_date"],
            "priority": "medium"
        })

        actions.append({
            "type": "sign_contract",
            "description": f"Sign contract with {', '.join(metadata.get('parties', []))}.",
            "deadline": metadata["termination_date"],
            "priority": "high"
        })
    return actions

def actions_for_earnings(metadata: Dict) -> List[Dict]:
    return [{
        "type": "review_report",
        "description": "Summarize or discuss report with stakeholders.",
        "priority": "low"
    },
    {
        "type": "prepare_presentation",
        "description": "Prepare a presentation based on the earnings report.",
        "priority": "low"
    }]

def actions_for_other(metadata: Dict) -> List[Dict]:
    return [{
        "type": "human_review",
        "description": "Review document for important information or actions. No specific metadata available.",
        "priority": "low"
    }]

ACTION_GENERATORS = {
    "Invoice": actions_for_invoice,
    "Contract": actions_for_contract,
    "Earnings": actions_for_earnings,
    "Other": actions_for_other
}
