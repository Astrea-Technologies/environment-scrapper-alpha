import textwrap

# Note: These prompts are designed for Claude 3 Sonnet.
# They request specific JSON structures matching PostAnalysis/CommentAnalysis schemas.

SENTIMENT_ANALYSIS_PROMPT_TEMPLATE = textwrap.dedent("""
    Analyze the sentiment of the following text:

    """{text}"""

    Provide the analysis as a JSON object with the following keys ONLY:
    - "sentiment_score": A float between -1.0 (very negative) and 1.0 (very positive), representing the overall sentiment.
    - "emotional_tone": A single descriptive word accurately reflecting the dominant emotion (e.g., neutral, angry, supportive, sarcastic, hopeful, critical, informative).
    - "key_phrases": A list of 1-5 short text excerpts (strings) from the original text that most strongly indicate the identified sentiment and tone.

    Respond ONLY with the valid JSON object, enclosed in ```json ... ``` tags if necessary, but preferably just the raw JSON.

    JSON Output:
""")

TOPIC_MODELING_PROMPT_TEMPLATE = textwrap.dedent("""
    Identify the main topics discussed in the following text:

    """{text}"""

    Provide the analysis as a JSON object with the following key ONLY:
    - "topics": A list of 1-3 concise strings (1-4 words each) representing the primary subjects or themes discussed.

    Respond ONLY with the valid JSON object, enclosed in ```json ... ``` tags if necessary, but preferably just the raw JSON.

    JSON Output:
""")

ENTITY_EXTRACTION_PROMPT_TEMPLATE = textwrap.dedent("""
    Extract named entities (people, organizations, locations, political figures, political parties, specific legislation/bills if mentioned) from the following text:

    """{text}"""

    Provide the analysis as a JSON object with the following key ONLY:
    - "entities_mentioned": A list of strings, where each string is a named entity found in the text. Include duplicates if an entity is mentioned multiple times. Focus on political context if applicable.

    Respond ONLY with the valid JSON object, enclosed in ```json ... ``` tags if necessary, but preferably just the raw JSON.

    JSON Output:
""")

COMBINED_ANALYSIS_PROMPT_TEMPLATE = textwrap.dedent("""
    Analyze the following text for sentiment, topics, and named entities:

    """{text}"""

    Provide the complete analysis as a single JSON object with the following keys ONLY:
    - "sentiment_score": A float between -1.0 (very negative) and 1.0 (very positive), representing the overall sentiment.
    - "emotional_tone": A single descriptive word accurately reflecting the dominant emotion (e.g., neutral, angry, supportive, sarcastic, hopeful, critical, informative).
    - "topics": A list of 1-3 concise strings (1-4 words each) representing the primary subjects or themes discussed.
    - "entities_mentioned": A list of strings, where each string is a named entity found in the text (people, organizations, locations, political figures/parties, specific legislation). Include duplicates if mentioned multiple times.

    Ensure the output is a single, valid JSON object. Respond ONLY with the JSON object, enclosed in ```json ... ``` tags if necessary, but preferably just the raw JSON.

    JSON Output:
""")

def format_prompt(template: str, text: str) -> str:
    """Formats a prompt template with the given text."""
    # Basic sanitization to prevent prompt injection issues, though LLM might still be vulnerable.
    # Consider more robust sanitization if handling untrusted user input directly in prompts.
    sanitized_text = text.replace('"', '\"').replace("\n", " ")
    return template.format(text=sanitized_text)