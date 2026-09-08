"""
Centralized Prompt Templates Directory for Autorag_champs.
Decouples prompt definitions from application business logic, supporting
dynamic variable injection and single-point prompt maintenance across features.
"""

def render_prompt(template: str, **values) -> str:
    """
    Renders a prompt template by injecting dynamic keyword variables into named placeholders.
    Example: render_prompt(RAG_ANSWER_TEMPLATE, vehicle_model="2023 SUV Model X", ...)
    """
    try:
        return template.format(**values)
    except KeyError as e:
        raise ValueError(f"Missing required prompt placeholder variable: {e}")

# 1. Grounded RAG Answer Template with Citation Rules
RAG_ANSWER_TEMPLATE = (
    "You are an expert service technician assistant for vehicle model {vehicle_model}.\n"
    "Rules:\n"
    "1. Answer the Question ONLY using the official service manual Context provided below.\n"
    "2. If the answer is not explicitly contained in the Context, respond strictly: 'I don't know based on available service data.'\n"
    "3. Keep your response concise (maximum 2 sentences).\n\n"
    "Vehicle Model: {vehicle_model}\n"
    "Fault Code: {dtc_code}\n"
    "Context:\n{context}\n\n"
    "Question: {question}"
)

# 2. Structured JSON Diagnostic Extraction Template
JSON_DIAGNOSTIC_TEMPLATE = (
    "You are an automated diagnostic manual parser.\n"
    "Extract specs from Manual ID '{manual_id}' and respond ONLY with a valid JSON object:\n"
    "{{\n"
    '  "manual_id": "{manual_id}",\n'
    '  "target_component": "string",\n'
    '  "primary_resistance_ohms": "string or null",\n'
    '  "torque_spec_nm": "string or null"\n'
    "}}\n\n"
    "Raw Manual Text:\n{raw_text}"
)

# 3. System Persona Configuration Template
SYSTEM_PERSONA_TEMPLATE = (
    "You are an automotive service diagnostic specialist operating in region {region_code}.\n"
    "Role Focus: {role_focus}.\n"
    "Always maintain a technical, concise, and safety-first tone."
)
