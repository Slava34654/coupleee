import datetime

from fastapi import APIRouter, Depends, HTTPException

try:
    from backend.models import EventIn
except ImportError:
    from models import EventIn


def next_annual(month: int, day: int, now: datetime.date) -> datetime.date:
    for year in range(now.year, now.year + 9):
        try:
            date = datetime.date(year, month, day)
        except ValueError:
            continue
        if date >= now:
            return date
    return datetime.date(now.year + 1, month, day)


def create_router(db, current_user, couple_of, sql_placeholders, utc_today, wsman):
    router = APIRouter(dependencies=[Depends(current_user)])

    @router.post("/events")
    async def event_add(body: EventIn):
        couple_of(body.user_id)
        datetime.date.fromisoformat(body.date)
        con = db()
        cursor = con.execute(
            "INSERT INTO events(user_id,title,date,icon,repeat) VALUES(?,?,?,?,?)",
            (body.user_id, body.title, body.date, body.icon, 1 if body.repeat else 0),
        )
        con.commit()
        con.close()
        await wsman.ping_couple(body.user_id, "events")
        return {"id": cursor.lastrowid}

    @router.get("/events")
    def events(user_id: int):
        _, partner = couple_of(user_id)
        ids = [user_id] + ([partner["id"]] if partner else [])
        placeholders = sql_placeholders(len(ids))
        con = db()
        rows = con.execute(
            "SELECT * FROM events WHERE user_id IN (" + placeholders + ")", ids
        ).fetchall()
        con.close()
        now = utc_today()
        result = []
        for row in rows:
            base = datetime.date.fromisoformat(row["date"])
            shown_date = row["date"]
            if row["repeat"]:
                next_date = next_annual(base.month, base.day, now)
                days_left = (next_date - now).days
                shown_date = next_date.isoformat()
            else:
                days_left = (base - now).days
            result.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "date": shown_date,
                    "days_left": days_left,
                    "icon": row["icon"] or "🎉",
                    "repeat": bool(row["repeat"]),
                }
            )
        result.sort(
            key=lambda event: (
                event["days_left"] < 0,
                abs(event["days_left"])
                if event["days_left"] >= 0
                else -event["days_left"],
            )
        )
        return result

    @router.delete("/events/{eid}")
    async def event_del(eid: int, user_id: int):
        _, partner = couple_of(user_id)
        ids = [user_id] + ([partner["id"]] if partner else [])
        con = db()
        row = con.execute("SELECT user_id FROM events WHERE id=?", (eid,)).fetchone()
        if not row:
            con.close()
            raise HTTPException(404, "event not found")
        if row["user_id"] not in ids:
            con.close()
            raise HTTPException(403, "not your event")
        con.execute("DELETE FROM events WHERE id=?", (eid,))
        con.commit()
        con.close()
        await wsman.ping_couple(user_id, "events")
        return {"ok": True}

    return router
