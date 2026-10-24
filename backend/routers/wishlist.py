from fastapi import APIRouter, Depends, HTTPException

try:
    from backend.models import WishlistDoneIn, WishlistIn
except ImportError:
    from models import WishlistDoneIn, WishlistIn


def create_router(db, current_user, couple_of, utc_iso, wsman):
    router = APIRouter(dependencies=[Depends(current_user)])

    def wishlist_couple(user_id: int):
        me, partner = couple_of(user_id)
        if not partner:
            raise HTTPException(400, "partner has not joined yet")
        key = f"{min(me['id'], partner['id'])}:{max(me['id'], partner['id'])}"
        return me, partner, key

    def wishlist_row(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "author_id": row["author_id"],
            "author": row["author"],
            "photo": row["photo"] or "",
            "done": bool(row["done"]),
            "created_at": row["created_at"],
            "completed_at": row["completed_at"] or "",
        }

    @router.get("/wishlist")
    def wishlist_get(user_id: int):
        _, _, pair_key = wishlist_couple(user_id)
        con = db()
        rows = con.execute(
            "SELECT w.*, u.name author FROM wishlist w "
            "JOIN users u ON u.id=w.author_id WHERE w.pair_key=? "
            "ORDER BY w.done, w.created_at DESC, w.id DESC",
            (pair_key,),
        ).fetchall()
        con.close()
        return [wishlist_row(row) for row in rows]

    @router.post("/wishlist")
    async def wishlist_add(body: WishlistIn):
        _, _, pair_key = wishlist_couple(body.user_id)
        title = body.title.strip()
        if not title or len(title) > 200:
            raise HTTPException(400, "title must contain 1 to 200 characters")
        photo = body.photo.strip()
        if len(photo) > 2000:
            raise HTTPException(400, "photo URL is too long")
        created_at = utc_iso()
        con = db()
        cursor = con.execute(
            "INSERT INTO wishlist(pair_key,author_id,title,photo,created_at) "
            "VALUES(?,?,?,?,?)",
            (pair_key, body.user_id, title, photo, created_at),
        )
        con.commit()
        con.close()
        await wsman.ping_couple(body.user_id, "wishlist")
        return {"id": cursor.lastrowid}

    @router.post("/wishlist/{item_id}/done")
    async def wishlist_done(item_id: int, body: WishlistDoneIn):
        _, _, pair_key = wishlist_couple(body.user_id)
        con = db()
        row = con.execute(
            "SELECT id FROM wishlist WHERE id=? AND pair_key=?", (item_id, pair_key)
        ).fetchone()
        if not row:
            con.close()
            raise HTTPException(404, "wishlist item not found")
        completed_at = utc_iso() if body.done else ""
        con.execute(
            "UPDATE wishlist SET done=?,completed_at=? WHERE id=?",
            (1 if body.done else 0, completed_at, item_id),
        )
        con.commit()
        con.close()
        await wsman.ping_couple(body.user_id, "wishlist")
        return {"ok": True}

    @router.delete("/wishlist/{item_id}")
    async def wishlist_delete(item_id: int, user_id: int):
        _, _, pair_key = wishlist_couple(user_id)
        con = db()
        row = con.execute(
            "SELECT id FROM wishlist WHERE id=? AND pair_key=?", (item_id, pair_key)
        ).fetchone()
        if not row:
            con.close()
            raise HTTPException(404, "wishlist item not found")
        con.execute("DELETE FROM wishlist WHERE id=?", (item_id,))
        con.commit()
        con.close()
        await wsman.ping_couple(user_id, "wishlist")
        return {"ok": True}

    return router
