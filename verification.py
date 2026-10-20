import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from models import PainPointCreate
from typing import List, Dict, Any

VALID_TAGS = ["Imaging", "Lab Work", "Cost", "Patient Communication", "Regulatory", "Process", "Technology", "Clinical"]

def verify_pain_point(disease_name: str, stage_name: str, new_pain_point: PainPointCreate, existing_descriptions: List[str]) -> Dict[str, Any]:
    """
    Uses ChatOllama to verify a new pain point.
    Checks for duplicates and clinical relevance.
    Also assigns severity (low/medium/high/critical) and tags.
    Returns a dict with 'approved' (bool), 'reason' (str), 'severity' (str), 'tags' (list).
    """
    llm = ChatOllama(model="llama3", temperature=0, format="json", num_ctx=8192)
    
    existing_list_str = "\n".join([f"- {desc}" for desc in existing_descriptions])
    valid_tags_str = ", ".join(VALID_TAGS)
    
    system_prompt = (
        "You are an expert medical AI assistant specialized in evaluating disease pathway pain points.\n"
        "Your task is to review a newly proposed pain point for a specific disease stage.\n"
        "You must output ONLY valid JSON matching this exact schema:\n"
        "{\n"
        '  "approved": boolean,\n'
        '  "reason": "string explaining why",\n'
        '  "severity": "low" | "medium" | "high" | "critical",\n'
        f'  "tags": ["array", "of", "relevant", "tags", "chosen", "from", "{valid_tags_str}"]\n'
        "}\n\n"
        "CRITERIA FOR REJECTION:\n"
        "1. DUPLICATE: The pain point is semantically identical or extremely similar to an existing pain point.\n"
        "2. IRRELEVANT: The pain point is nonsensical or unrelated to a clinical or process issue for the disease.\n\n"
        "SEVERITY GUIDELINES:\n"
        "- critical: life-threatening, blocks diagnosis/treatment, affects most patients\n"
        "- high: significantly impacts patient outcomes or workflow efficiency\n"
        "- medium: notable inconvenience or inefficiency with moderate impact\n"
        "- low: minor issue, easily worked around\n\n"
        "TAGS: Choose 1-3 most relevant tags from the allowed list.\n"
        "If it is valid and not a duplicate, set approved to true."
    )
    
    user_prompt = (
        f"DISEASE: {disease_name}\n"
        f"STAGE: {stage_name}\n\n"
        f"EXISTING PAIN POINTS IN THIS STAGE:\n"
        f"{existing_list_str if existing_descriptions else 'None'}\n\n"
        f"PROPOSED NEW PAIN POINT:\n"
        f"Description: {new_pain_point.description}\n"
        f"Sources: {new_pain_point.sources or 'N/A'}\n"
        f"Coverage: {new_pain_point.coverage or 'N/A'}\n"
        f"Existing Solutions: {new_pain_point.existing_solutions or 'N/A'}\n\n"
        "Evaluate the proposed new pain point and return the JSON."
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        result = json.loads(response.content)
        
        # Validate and sanitize severity
        severity = result.get("severity", "medium")
        if severity not in ["low", "medium", "high", "critical"]:
            severity = "medium"
        
        # Validate and sanitize tags
        raw_tags = result.get("tags", [])
        if isinstance(raw_tags, list):
            tags = [t for t in raw_tags if t in VALID_TAGS][:3]
        else:
            tags = []
        
        return {
            "approved": result.get("approved", False),
            "reason": result.get("reason", "No reason provided by LLM."),
            "severity": severity,
            "tags": tags
        }
    except Exception as e:
        # If the AI verification service (Ollama) is unavailable,
        # auto-approve the pain point rather than blocking the user.
        return {
            "approved": True,
            "reason": f"Auto-approved (AI verification unavailable: {str(e)})",
            "severity": "medium",
            "tags": []
        }


def classify_existing_pain_point(description: str, disease_name: str = "") -> Dict[str, Any]:
    """
    Classify an existing pain point (already in DB) with severity and tags.
    Used for batch processing existing data.
    """
    llm = ChatOllama(model="llama3", temperature=0, format="json", num_ctx=4096)
    valid_tags_str = ", ".join(VALID_TAGS)
    
    system_prompt = (
        "You are a medical AI assistant. Classify the following clinical pain point.\n"
        "Output ONLY valid JSON:\n"
        "{\n"
        '  "severity": "low" | "medium" | "high" | "critical",\n'
        f'  "tags": ["array", "of", "tags", "from", "{valid_tags_str}"]\n'
        "}\n\n"
        "SEVERITY: critical=life-threatening, high=significant impact, medium=moderate, low=minor.\n"
        "TAGS: Choose 1-3 most relevant."
    )
    
    user_prompt = f"DISEASE: {disease_name}\nPAIN POINT: {description}\n\nClassify this pain point."
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        result = json.loads(response.content)
        severity = result.get("severity", "medium")
        if severity not in ["low", "medium", "high", "critical"]:
            severity = "medium"
        raw_tags = result.get("tags", [])
        tags = [t for t in raw_tags if t in VALID_TAGS][:3] if isinstance(raw_tags, list) else []
        return {"severity": severity, "tags": tags}
    except Exception:
        return {"severity": "medium", "tags": []}
