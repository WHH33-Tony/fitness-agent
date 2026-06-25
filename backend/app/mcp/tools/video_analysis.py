from app.services.pose_service import analyze_landmarks


def video_analysis_tool(movement_name: str, landmarks: list[dict[str, float]]) -> dict:
    return analyze_landmarks(movement_name, landmarks)
