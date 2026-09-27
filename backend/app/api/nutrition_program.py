from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import NutritionProgramModel, UserModel
from app.schemas.nutrition_program import (
    CancelProgramRequest,
    DailyLogRequest,
    DailyLogResponse,
    ExtensionCreateRequest,
    FinalProgramResultResponse,
    ExtensionRecommendationResponse,
    BlockReviewResponse,
    ProgramStateRequest,
    SafetyReviewRequest,
    NutritionProgramCreateRequest,
    ProgramDayDetailResponse,
    ProgramDetailResponse,
    ProgramEvaluationResponse,
    ProgramProgressResponse,
    ProgramSummaryResponse,
)
from app.services.nutrition_program_service import (
    apply_daily_log,
    cancel_program,
    create_extension,
    delete_cancelled_program,
    create_program,
    evaluate_program,
    final_program_result,
    extension_recommendation,
    block_review,
    pause_program,
    resume_program,
    review_safety_hold,
    skip_current_day,
    active_rule_version,
    owned_program,
    progress_for,
    serialize_day_detail,
    serialize_detail,
    serialize_summary,
)

router = APIRouter(prefix="/api/nutrition", tags=["nutrition-program"])


@router.post("/program", response_model=ProgramSummaryResponse, status_code=201)
def create(
    payload: NutritionProgramCreateRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    program = create_program(
        db,
        user,
        payload.assessment,
        consent_to_save=payload.consent_to_save,
        duration_days=payload.duration_days,
        goal_key=payload.goal_key,
        display_name=payload.display_name,
    )
    return serialize_summary(db, program)


@router.get("/program", response_model=list[ProgramSummaryResponse])
def list_programs(user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(NutritionProgramModel)
        .where(NutritionProgramModel.user_id == user.id)
        .order_by(NutritionProgramModel.created_at.desc())
    ).all()
    return [serialize_summary(db, row) for row in rows]


@router.get("/history", response_model=list[ProgramSummaryResponse])
def history(user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_programs(user, db)


@router.get("/history/{program_id}", response_model=ProgramDetailResponse)
def history_detail(program_id: str, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_detail(db, owned_program(db, user, program_id))


@router.get("/program/{program_id}", response_model=ProgramDetailResponse)
def detail(program_id: str, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_detail(db, owned_program(db, user, program_id))


@router.get("/program/{program_id}/days/{day_number}", response_model=ProgramDayDetailResponse)
def day_detail(
    program_id: str,
    day_number: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return serialize_day_detail(db, owned_program(db, user, program_id), day_number)


@router.post("/program/{program_id}/daily-log", response_model=DailyLogResponse)
def daily_log(
    program_id: str,
    payload: DailyLogRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return apply_daily_log(db, owned_program(db, user, program_id), payload)


@router.get("/program/{program_id}/progress", response_model=ProgramProgressResponse)
def progress(program_id: str, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return progress_for(db, owned_program(db, user, program_id))


@router.get("/rules/active")
def rules_active(user: UserModel = Depends(get_current_user)):
    return active_rule_version()


@router.get("/program/{program_id}/block-review", response_model=BlockReviewResponse)
def program_block_review(program_id: str, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return block_review(db, owned_program(db, user, program_id))


@router.post("/program/{program_id}/pause", response_model=ProgramSummaryResponse)
def pause(program_id: str, payload: ProgramStateRequest, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_summary(db, pause_program(db, owned_program(db, user, program_id), confirm=payload.confirm))


@router.post("/program/{program_id}/resume", response_model=ProgramSummaryResponse)
def resume(program_id: str, payload: ProgramStateRequest, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_summary(
        db,
        resume_program(
            db,
            owned_program(db, user, program_id),
            confirm=payload.confirm,
            recovery_status=payload.recovery_status,
        ),
    )


@router.post("/program/{program_id}/skip-day", response_model=ProgramProgressResponse)
def skip_day(program_id: str, payload: ProgramStateRequest, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return skip_current_day(db, owned_program(db, user, program_id), confirm=payload.confirm)


@router.post("/program/{program_id}/safety-review", response_model=ProgramSummaryResponse)
def safety_review(program_id: str, payload: SafetyReviewRequest, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    program = owned_program(db, user, program_id)
    return serialize_summary(db, review_safety_hold(db, program, confirm=payload.confirm, action=payload.action, goal_key=payload.goal_key))


@router.post("/program/{program_id}/cancel", response_model=ProgramSummaryResponse)
def cancel(
    program_id: str,
    payload: CancelProgramRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    program = owned_program(db, user, program_id)
    return serialize_summary(db, cancel_program(db, program, confirm=payload.confirm))


@router.delete("/program/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program(
    program_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    program = owned_program(db, user, program_id)
    delete_cancelled_program(db, program)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/program/{program_id}/evaluation", response_model=ProgramEvaluationResponse)
def evaluation(program_id: str, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return evaluate_program(db, owned_program(db, user, program_id))


@router.get("/program/{program_id}/result", response_model=FinalProgramResultResponse)
def result(program_id: str, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return final_program_result(db, owned_program(db, user, program_id))


@router.get("/program/{program_id}/extension-recommendation", response_model=ExtensionRecommendationResponse)
def extension_info(program_id: str, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    return extension_recommendation(db, owned_program(db, user, program_id))


@router.post("/program/{program_id}/extend", response_model=ProgramSummaryResponse, status_code=201)
def extend(
    program_id: str,
    payload: ExtensionCreateRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    program = owned_program(db, user, program_id)
    return serialize_summary(db, create_extension(db, user, program, confirm=payload.confirm, preference=payload.preference, difficulty=payload.difficulty, goal_key=payload.goal_key))
