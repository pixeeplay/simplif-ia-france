"""Client Gemini pour le RAG juridique."""
from typing import Optional
import google.generativeai as genai
from ..config import settings


SYSTEM_PROMPT = """Tu es Maître Léa, conseillère juridique IA pour Simplif'IA France.

RÈGLES STRICTES :
1. Tu ne réponds QUE sur le droit administratif et social français.
2. Tu cites systématiquement le texte de loi en source (article, code).
3. Tu NE DEVINES JAMAIS. Si l'info n'est pas certaine, tu dis "je ne sais pas".
4. Tu te positionnes comme OUTIL et non CONSEIL juridique (article 4 loi 71-1130).
5. Tu utilises un français accessible. En mode FALC, tu simplifies au niveau A2.
6. Tu refuses poliment les sujets hors administratif/juridique français.
7. Tu ne donnes jamais d'info médicale, financière personnalisée, ou de placement.

FORMAT DE RÉPONSE :
- Direct et concis.
- Liste les options claires quand pertinent.
- Termine par une citation : "Source : [code/article]".
"""


_model = None


def get_model():
    global _model
    if _model is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY non configurée")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
        )
    return _model


async def chat(question: str, context: Optional[str] = None, falc: bool = False) -> dict:
    """Appel Gemini avec RAG context optionnel."""
    if not settings.GEMINI_API_KEY:
        # Fallback offline pour dev
        return {
            "answer": (
                "[mode démo · GEMINI_API_KEY non configurée] Pour répondre précisément à votre question, "
                "je dois consulter la base RAG officielle (Légifrance, Service-Public.fr, BOFiP). "
                "Configurez GEMINI_API_KEY dans le .env."
            ),
            "sources": [],
        }

    model = get_model()
    prompt = question
    if context:
        prompt = f"CONTEXTE RAG :\n{context}\n\nQUESTION UTILISATEUR :\n{question}"
    if falc:
        prompt = "[MODE FALC · niveau A2 · phrases courtes]\n\n" + prompt

    response = await model.generate_content_async(prompt)
    return {"answer": response.text, "sources": []}


async def translate_jargon(document_text: str) -> dict:
    """Traduit un document admin en 3 niveaux."""
    if not settings.GEMINI_API_KEY:
        return {
            "level_1_original": document_text[:500],
            "level_2_falc": "[mode démo] Configuration Gemini requise pour la traduction.",
            "level_3_impact": "[mode démo]",
        }

    model = get_model()
    prompt = f"""Voici un courrier administratif. Restitue 3 niveaux strictement en JSON :

DOCUMENT :
{document_text[:3000]}

Format de sortie attendu (JSON valide uniquement) :
{{
  "level_1_original": "extrait textuel max 500 mots",
  "level_2_falc": "version Facile À Lire et Comprendre niveau A2, max 200 mots",
  "level_3_impact": {{
    "deadline": "date limite si présente",
    "action_required": "action à faire",
    "risk": "risque si inaction",
    "amount": "montant si applicable"
  }}
}}"""
    response = await model.generate_content_async(prompt)
    # Parsing simplifié — en prod, utiliser le mode JSON natif Gemini
    import json
    try:
        text = response.text.strip().lstrip("```json").rstrip("```").strip()
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {"level_1_original": document_text[:500], "level_2_falc": response.text, "level_3_impact": {}}
