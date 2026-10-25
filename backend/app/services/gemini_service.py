import logging
from typing import List, Dict, Any, Optional
from app.config import settings
from app.database import db

logger = logging.getLogger("gemini_service")

class GeminiAssistantService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = None
        self.is_active = False
        self._init_gemini()

    def _init_gemini(self):
        if not self.api_key:
            self.is_active = False
            logger.info("Gemini API key not configured. AI Financial Assistant is in offline / simulated mode.")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            # Try available model names in order of preference
            candidate_models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-1.5-flash", "gemini-pro"]
            selected_model = None
            for name in candidate_models:
                try:
                    m = genai.GenerativeModel(name)
                    selected_model = m
                    logger.info(f"Initialized Gemini model: {name}")
                    break
                except Exception:
                    continue

            if selected_model:
                self.model = selected_model
                self.is_active = True
            else:
                self.model = genai.GenerativeModel("gemini-2.5-flash")
                self.is_active = True
        except Exception as e:
            logger.warning(f"Could not initialize Google Generative AI: {e}")
            self.is_active = False

    def answer_query(self, user_query: str, company_focus: Optional[str] = None) -> Dict[str, Any]:
        """
        Grounds user query in actual stored financial news articles and FinBERT sentiment records.
        Does not fabricate articles, sources, or market predictions.
        """
        # Fetch relevant context articles
        all_articles = db.find("news_articles", limit=100)
        relevant = []

        q_lower = user_query.lower()
        for a in all_articles:
            if a.get("is_duplicate"):
                continue
            title = (a.get("title") or "").lower()
            company = (a.get("company") or "").lower()
            if company_focus and company_focus.lower() in company:
                relevant.append(a)
            elif any(w in title or w in company for w in q_lower.split() if len(w) > 3):
                relevant.append(a)

        # If none matched specific keywords, provide top 5 recent articles
        if not relevant:
            relevant = all_articles[:5]

        # Extract citation references
        citations = []
        for a in relevant[:4]:
            citations.append({
                "title": a.get("title"),
                "source": a.get("source"),
                "url": a.get("url"),
                "sentiment": a.get("sentiment"),
                "confidence": a.get("confidence"),
                "company": a.get("company")
            })

        disclaimer = "AI Financial Assistant responses are grounded solely in available news tone and FinBERT sentiment classifications. This does not constitute investment advice."

        if not self.is_active or not self.model:
            # Transparent fallback response when Gemini key is not configured
            if not citations:
                answer = (
                    "No relevant financial articles were found in the current sentiment database. "
                    "Please search for another company or ingest fresh news articles."
                )
            else:
                summary_lines = [
                    f"• {c['company']} ({c['sentiment'].upper()} - {int(c['confidence']*100)}% conf): \"{c['title']}\" [Source: {c['source']}]"
                    for c in citations
                ]
                answer = (
                    f"Gemini API key is not configured in this environment (Assistant offline mode). "
                    f"However, based on currently indexed news records, here is the sentiment context for your query:\n\n"
                    + "\n".join(summary_lines)
                    + "\n\nTo enable conversational synthesis, set GEMINI_API_KEY in backend/.env."
                )
            return {
                "response": answer,
                "relevant_articles": citations,
                "is_gemini_active": False,
                "disclaimer": disclaimer
            }

        # Generate conversational answer with Gemini RAG
        context_prompt = (
            "You are an AI Financial News Intelligence Assistant. "
            "Analyze the user's question using ONLY the provided verified news articles and FinBERT sentiment scores.\n"
            "Rules:\n"
            "1. Ground your answer strictly in the provided articles. Do NOT fabricate facts, URLs, or news sources.\n"
            "2. Clarify that FinBERT measures sentiment and tone, not future stock performance.\n"
            "3. If there is insufficient data to answer, say so honestly.\n\n"
            f"Context Articles:\n"
        )
        for i, c in enumerate(citations):
            context_prompt += (
                f"[{i+1}] Company: {c['company']} | Sentiment: {c['sentiment']} ({c['confidence']:.2f}) | "
                f"Headline: {c['title']} | Source: {c['source']} | URL: {c['url']}\n"
            )

        context_prompt += f"\nUser Query: {user_query}\n\nProvide a professional, objective financial intelligence summary:"

        try:
            response = self.model.generate_content(context_prompt)
            answer_text = response.text
        except Exception as e:
            logger.warning(f"Gemini API generation error: {e}. Falling back to structured grounded synthesis.")
            lines = [
                f"• {c['company']} ({c['sentiment'].upper()} - {int(c['confidence']*100)}% conf): \"{c['title']}\" [{c['source']}]"
                for c in citations
            ]
            answer_text = (
                "Here is the verified sentiment intelligence grounded in currently indexed financial news:\n\n"
                + "\n".join(lines)
                + "\n\n(Conversational synthesis service temporarily unavailable; raw news context shown above.)"
            )

        return {
            "response": answer_text,
            "relevant_articles": citations,
            "is_gemini_active": True,
            "disclaimer": disclaimer
        }

gemini_assistant_service = GeminiAssistantService()
