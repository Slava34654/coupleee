import random

from fastapi import APIRouter, Depends, HTTPException

try:
    from backend.models import IdeaIn
except ImportError:
    from models import IdeaIn


def create_routers(db, current_user):
    public = APIRouter()
    protected = APIRouter(dependencies=[Depends(current_user)])

    @public.get("/ideas")
    def ideas(category: str = "", budget: str = ""):
        con = db()
        query, args = "SELECT * FROM ideas WHERE 1=1", []
        if category:
            query += " AND category=?"
            args.append(category)
        if budget:
            query += " AND budget=?"
            args.append(budget)
        rows = con.execute(query, args).fetchall()
        con.close()
        return [dict(row) for row in rows]

    @public.get("/idea/random")
    def idea_random():
        con = db()
        rows = con.execute("SELECT * FROM ideas WHERE done=0").fetchall()
        con.close()
        if not rows:
            raise HTTPException(404, "no ideas left")
        return dict(random.choice(rows))

    @protected.post("/ideas")
    async def idea_add(body: IdeaIn):
        con = db()
        cursor = con.execute(
            "INSERT INTO ideas(title,category,budget) VALUES(?,?,?)",
            (body.title, body.category, body.budget),
        )
        con.commit()
        con.close()
        return {"id": cursor.lastrowid}

    @protected.post("/idea/{iid}/done")
    async def idea_done(iid: int, done: bool = True):
        con = db()
        con.execute("UPDATE ideas SET done=? WHERE id=?", (1 if done else 0, iid))
        con.commit()
        con.close()
        return {"ok": True}

    return public, protected
