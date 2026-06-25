from app.services.pose_service import analyze_landmarks


def pose_analysis_tool(movement_name: str, landmarks: list[dict]) -> dict:
    return analyze_landmarks(movement_name, landmarks)

