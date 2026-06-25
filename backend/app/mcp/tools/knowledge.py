from app.services.qa_service import retrieve_knowledge


def knowledge_tool(question: str) -> dict:
    return {"snippets": retrieve_knowledge(question)}
