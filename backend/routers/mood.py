from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

try:
    from backend.models import MoodIn
except ImportError:
    from models import MoodIn


def create_router(db, current_user, couple_of, utc_iso, wsman, send_mood_push):
    router = APIRouter(dependencies=[Depends(current_user)])

    @router.post("/mood")
    async def set_mood(body: MoodIn, background_tasks: BackgroundTasks):
        me, partner = couple_of(body.user_id)
        mood = body.mood.strip()
        note = body.note.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not mood and note:
            mood = "💬"
        if not mood:
            raise HTTPException(400, "mood or note is required")
        if len(mood) > 32:
            raise HTTPException(400, "mood is too long")
        if len(note) > 120:
            raise HTTPException(400, "mood message is too long")
        con = db()
        con.execute(
            "INSERT INTO moods(user_id,mood,note,ts) VALUES(?,?,?,?)",
            (body.user_id, mood, note, utc_iso()),
        )
        con.commit()
        con.close()
        await wsman.ping_couple(body.user_id, "mood")
        if partner:
            background_tasks.add_task(
                send_mood_push, partner["id"], me["name"], mood, note
            )
        return {"ok": True}

    return router
