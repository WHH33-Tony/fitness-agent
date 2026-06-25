from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, UsersDb
from app.models.users import TrainingPlan, UserQuestionnaire
from app.schemas import QuestionnaireIn
from app.services.plan_service import generate_training_plan

router = APIRouter(prefix="/plans", tags=["个性化推荐"])


@router.post("/questionnaire")
def submit_questionnaire(payload: QuestionnaireIn, current_user: CurrentUser, db: UsersDb) -> dict:
    questionnaire = db.get(UserQuestionnaire, current_user.id) or UserQuestionnaire(user_id=current_user.id)
    questionnaire.physique = payload.physique
    questionnaire.fitness_goal = payload.fitness_goal
    questionnaire.exercise_level = payload.exercise_level
    questionnaire.injury_history = payload.injury_history
    questionnaire.avoid_movements = payload.avoid_movements
    questionnaire.extra_info = payload.extra_info
    db.merge(questionnaire)

    plan_data = generate_training_plan(payload)
    plan = TrainingPlan(user_id=current_user.id, name=f"{payload.fitness_goal or '综合'}训练计划", plan_data=plan_data)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {"message": "训练计划已生成", "plan": {"id": plan.id, "name": plan.name, "plan_data": plan.plan_data}}


@router.get("")
def list_plans(current_user: CurrentUser, db: UsersDb) -> list[dict]:
    rows = db.scalars(select(TrainingPlan).where(TrainingPlan.user_id == current_user.id).order_by(TrainingPlan.generated_at.desc())).all()
    return [
        {
            "id": plan.id,
            "name": plan.name,
            "plan_data": plan.plan_data,
            "generated_at": plan.generated_at.isoformat() if plan.generated_at else None,
        }
        for plan in rows
    ]
