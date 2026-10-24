import datetime

from fastapi import APIRouter, Depends

try:
    from backend.models import TogetherIn
except ImportError:
    from models import TogetherIn


def create_router(db, current_user, couple_of, check_since, utc_today, wsman):
    router = APIRouter(dependencies=[Depends(current_user)])

    def premium_active(premium_until: str) -> bool:
        try:
            return (
                bool(premium_until)
                and datetime.date.fromisoformat(premium_until) >= utc_today()
            )
        except ValueError:
            return False

    def couple_premium_until(me, partner) -> str:
        active_until = []
        for user in (me, partner):
            if user is None or "premium_until" not in user.keys():
                continue
            until = user["premium_until"] or ""
            if premium_active(until):
                active_until.append(until)
        return max(active_until, default="")

    @router.get("/premium")
    def premium_status(user_id: int):
        me, partner = couple_of(user_id)
        until = couple_premium_until(me, partner)
        email = me["email"] or "" if "email" in me.keys() else ""
        return {"premium": bool(until), "until": until, "email": email}

    @router.post("/together")
    async def together_set(body: TogetherIn):
        _, partner = couple_of(body.user_id)
        date = check_since(body.date)
        con = db()
        con.execute(
            "UPDATE users SET together_since=? WHERE id=?", (date, body.user_id)
        )
        if partner:
            con.execute(
                "UPDATE users SET together_since=? WHERE id=?", (date, partner["id"])
            )
        con.commit()
        con.close()
        await wsman.ping_couple(body.user_id, "pair")
        days = (utc_today() - datetime.date.fromisoformat(date)).days
        return {"date": date, "days": days}

    return router
