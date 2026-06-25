import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api import auth, config, exercises, feedback, mcp_admin, plans, pose, qa, sports, users
from app.core.config import get_settings
from app.core.runtime_config import bootstrap_runtime_settings
from app.core.database import SportsBase, UsersBase, sports_engine, users_engine
from app.services.food_seed import sync_nutrition_foods
from app.services.mcp_bootstrap import bootstrap_mcp_tools
from app.models.users import User, UserProfile

settings = get_settings()
logger = logging.getLogger(__name__)


def _init_sqlite() -> None:
    # For desktop distribution we allow SQLite URLs and auto-create tables.
    try:
        # Ensure upload dir exists (packaged apps may run under non-writable CWD).
        try:
            os.makedirs(settings.upload_dir, exist_ok=True)
        except Exception:
            pass

        if settings.users_database_url.startswith("sqlite"):
            UsersBase.metadata.create_all(bind=users_engine)

            # Seed a default admin account only on first run (empty users table).
            with Session(bind=users_engine) as db:
                user_count = db.scalar(select(func.count()).select_from(User)) or 0
                if user_count == 0:
                    admin_user = User(phone="admin", password_hash="plain:123456", role="admin")
                    db.add(admin_user)
                    db.flush()  # assign admin_user.id

                    db.add(
                        UserProfile(
                            user_id=admin_user.id,
                            nickname="系统管理员",
                            height=175.0,
                            weight=70.0,
                            gender="unknown",
                            age=22,
                        )
                    )
                    db.commit()
                    logger.info("SQLite首次启动，已创建默认管理员: admin/123456")

        if settings.sports_database_url.startswith("sqlite"):
            os.makedirs("data", exist_ok=True)
            with Session(bind=sports_engine) as sdb:
                ddl_row = sdb.execute(
                    text("SELECT sql FROM sqlite_master WHERE type='table' AND name='nutrition_foods'")
                ).fetchone()
                ddl = str(ddl_row[0] or "") if ddl_row else ""
                # 旧版表用 BIGINT 主键且无自增，会导致种子数据插入失败
                if ddl and "BIGINT" in ddl.upper() and "AUTOINCREMENT" not in ddl.upper():
                    sdb.execute(text("DROP TABLE nutrition_foods"))
                    sdb.commit()
                    logger.warning("检测到 nutrition_foods 表结构不兼容，已自动重建")

            SportsBase.metadata.create_all(bind=sports_engine)
            # Seed nutrition foods for desktop SQLite (migrate + upsert).
            with Session(bind=sports_engine) as sdb:
                try:
                    cols = [row[1] for row in sdb.execute(text("PRAGMA table_info(nutrition_foods)")).all()]
                    if cols and "category" not in cols:
                        sdb.execute(text("ALTER TABLE nutrition_foods ADD COLUMN category VARCHAR(64)"))
                        sdb.commit()
                except Exception:
                    pass

                added, updated = sync_nutrition_foods(sdb)
                if added or updated:
                    logger.info("营养食物库已同步：新增 %s 条，更新 %s 条", added, updated)
    except Exception:
        logger.exception("SQLite 初始化失败")
        return

    # If schema changed (e.g. primary key type for SQLite autoincrement), old db may be incompatible.
    # Best-effort: if users db exists but basic write fails later, the app can't be used anyway.
    # Here we only handle the common case: fresh desktop DB with broken schema from older build.
    try:
        if settings.users_database_url.startswith("sqlite"):
            url = settings.users_database_url
            if url.startswith("sqlite:///"):
                db_path = url.replace("sqlite:///", "", 1)
                db_path = db_path.replace("/", os.sep)
                if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
                    # ensure tables exist with current metadata; if not, recreate from scratch
                    # We'll detect by checking for a users row insertability is hard without a session here;
                    # keep this as a no-op placeholder for compatibility.
                    pass
    except Exception:
        return


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    bootstrap_runtime_settings()
    _init_sqlite()
    bootstrap_mcp_tools()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(sports.router, prefix="/api")
app.include_router(exercises.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
app.include_router(pose.router, prefix="/api")
app.include_router(qa.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(mcp_admin.router, prefix="/api")
app.include_router(config.router, prefix="/api")

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
