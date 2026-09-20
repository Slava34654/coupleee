"""CoupleJoy — десктоп-демо (Tkinter, тёмная тема) поверх Python-бэкенда.
Требует запущенный backend: uvicorn main:app --port 8000 (каталог backend/).
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
BG, CARD, FG, MUT = "#141021", "#221b3a", "#f4efff", "#a79fd1"
PINK, GOLD, GREEN = "#ff5d8f", "#ffd166", "#2ed573"

def api(method, path, body=None, params=None):
    url = BASE + path
    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode())["detail"]
        except Exception:
            detail = e.reason
        raise RuntimeError(detail)
    except Exception as e:
        raise RuntimeError(f"нет связи с сервером ({e}). Запусти backend!")

class App:
    def __init__(self, root):
        self.root = root
        root.title("💑 CoupleJoy — демо")
        root.geometry("560x680")
        root.configure(bg=BG)
        self.uid = None
        st = ttk.Style(root)
        st.theme_use("clam")
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", background="#241d42", foreground=FG,
                     padding=(12, 6), font=("", 10, "bold"))
        st.map("TNotebook.Tab", background=[("selected", PINK)],
               foreground=[("selected", "white")])
        st.configure("TFrame", background=BG)
        st.configure("Card.TFrame", background=CARD, relief="flat")
        st.configure("TLabel", background=BG, foreground=FG, font=("", 11))
        st.configure("Title.TLabel", font=("", 20, "bold"), foreground=PINK)
        st.configure("Head.TLabel", font=("", 14, "bold"), foreground=GOLD)
        st.configure("TButton", background=PINK, foreground="white",
                     font=("", 10, "bold"), padding=6, borderwidth=0)
        st.map("TButton", background=[("active", "#ff7aa5"), ("disabled", "#5a4a6e")])
        st.configure("Ghost.TButton", background="#2d2452", foreground=FG)
        st.map("Ghost.TButton", background=[("active", "#3d3170")])
        st.configure("TEntry", fieldbackground="#0f0b1e", foreground=FG,
                     insertcolor=FG, padding=6)
        st.configure("TListbox", background="#0f0b1e", foreground=FG)

        head = tk.Frame(root, bg=BG)
        head.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(head, text="💑  CoupleJoy", bg=BG, fg=PINK,
                 font=("", 22, "bold")).pack(side="left")
        tk.Label(head, text="для двоих", bg=BG, fg=MUT,
                 font=("", 11, "italic")).pack(side="left", padx=8, pady=(8, 0))

        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabs = {}
        for name in ["Пара", "Главная", "Вопрос", "Идеи", "Журнал", "События"]:
            f = ttk.Frame(self.nb, padding=12)
            self.nb.add(f, text=name)
            self.tabs[name] = f
        self.build_pair()
        self.build_home()
        self.build_daily()
        self.build_ideas()
        self.build_journal()
        self.build_events()

    # ---------- helpers ----------
    def err(self, fn):
        try:
            fn()
        except RuntimeError as e:
            messagebox.showerror("Ошибка", str(e))

    def card(self, parent):
        outer = tk.Frame(parent, bg="#0e0a1c", pady=1)
        outer.pack(fill="x", pady=6)
        inner = tk.Frame(outer, bg=CARD, padx=12, pady=10)
        inner.pack(fill="x", padx=1, pady=1)
        return inner

    def title(self, parent, text):
        tk.Label(parent, text=text, bg=BG, fg=GOLD,
                 font=("", 14, "bold")).pack(anchor="w", pady=(0, 2))

    # ---------- Пара ----------
    def build_pair(self):
        f = self.tabs["Пара"]
        self.title(f, "👥 Ваша пара")
        c = self.card(f)
        tk.Label(c, text="Ваше имя:", bg=CARD, fg=FG).pack(anchor="w")
        self.e_name = ttk.Entry(c, width=32); self.e_name.pack(anchor="w", pady=4)
        tk.Button(c, text="💗  Создать пару", bg=PINK, fg="white",
                  activebackground="#ff7aa5", font=("", 10, "bold"), relief="flat",
                  padx=12, pady=6,
                  command=lambda: self.err(self.do_create)).pack(anchor="w", pady=4)
        self.l_code = tk.Label(c, text="", bg=CARD, fg=GOLD, font=("", 16, "bold"))
        self.l_code.pack(anchor="w")
        c2 = self.card(f)
        tk.Label(c2, text="Код партнёра:", bg=CARD, fg=FG).pack(anchor="w")
        self.e_code = ttk.Entry(c2, width=32); self.e_code.pack(anchor="w", pady=4)
        tk.Button(c2, text="🤝  Присоединиться", bg=PINK, fg="white",
                  activebackground="#ff7aa5", font=("", 10, "bold"), relief="flat",
                  padx=12, pady=6,
                  command=lambda: self.err(self.do_join)).pack(anchor="w", pady=4)
        self.l_me = tk.Label(f, text="Пока вы не в паре", bg=BG, fg=MUT)
        self.l_me.pack(anchor="w", pady=6)

    def do_create(self):
        r = api("POST", "/pair", {"name": self.e_name.get()})
        self.uid = r["user_id"]
        self.l_code.config(text=f'🎟 Ваш код: {r["pair_code"]}')
        self.l_me.config(text=f'Вы #{self.uid}. Партнёр вводит код выше.',
                         fg=GREEN)
        self.refresh_home()

    def do_join(self):
        r = api("POST", "/pair/join",
                {"name": self.e_name.get(), "code": self.e_code.get()})
        self.uid = r["user_id"]
        self.l_me.config(text=f'Вы #{self.uid} — вы в паре! 💞', fg=GREEN)
        self.refresh_home()

    # ---------- Главная ----------
    def build_home(self):
        f = self.tabs["Главная"]
        self.title(f, "🏠 Главная")
        c = self.card(f)
        self.l_home = tk.Label(c, text="Сначала вкладка «Пара»",
                               bg=CARD, fg=FG, font=("", 12, "bold"),
                               justify="left")
        self.l_home.pack(anchor="w")
        c2 = self.card(f)
        tk.Label(c2, text="Моё настроение:", bg=CARD, fg=FG,
                 font=("", 11, "bold")).pack(anchor="w")
        row = tk.Frame(c2, bg=CARD); row.pack(anchor="w", pady=6)
        for m in ["😍", "🥰", "😊", "😢", "😡"]:
            tk.Button(row, text=m, font=("", 16), bg="#2d2452", relief="flat",
                      padx=6, pady=2,
                      command=lambda m=m: self.err(lambda: self.do_mood(m))).pack(
                          side="left", padx=3)
        tk.Button(f, text="🔄  Обновить", bg="#2d2452", fg=FG,
                  activebackground="#3d3170", relief="flat", padx=12, pady=6,
                  command=lambda: self.err(self.refresh_home)).pack(anchor="w")

    def do_mood(self, m):
        api("POST", "/mood", {"user_id": self.uid, "mood": m})
        self.refresh_home()

    def refresh_home(self):
        if not self.uid:
            return
        me = api("GET", "/me", params={"user_id": self.uid})
        p = me["partner"]
        self.l_home.config(
            text=f'💞 Вместе уже {me["days_together"]} дн.    🔥 Серия: {me["streak"]}\n'
                 f'👤 Партнёр: {p["name"] if p else "ждём…"}\n'
                 f'😊 Я: {(me["my_mood"] or {}).get("mood", "—")}\n'
                 f'💜 Партнёр: {(me["partner_mood"] or {}).get("mood", "—")}')

    # ---------- Вопрос ----------
    def build_daily(self):
        f = self.tabs["Вопрос"]
        self.title(f, "❓ Вопрос дня")
        c = self.card(f)
        self.l_q = tk.Label(c, text="Нажмите «Обновить»", bg=CARD, fg=FG,
                            font=("", 12, "bold"), wraplength=460, justify="left")
        self.l_q.pack(anchor="w")
        self.e_ans = ttk.Entry(f, width=52); self.e_ans.pack(anchor="w", pady=6)
        tk.Button(f, text="💌  Ответить", bg=PINK, fg="white",
                  activebackground="#ff7aa5", font=("", 10, "bold"),
                  relief="flat", padx=12, pady=6,
                  command=lambda: self.err(self.do_answer)).pack(anchor="w")
        c2 = self.card(f)
        self.l_ans = tk.Label(c2, text="", bg=CARD, fg=FG, wraplength=460,
                              justify="left")
        self.l_ans.pack(anchor="w")
        tk.Button(f, text="🔄  Обновить", bg="#2d2452", fg=FG,
                  activebackground="#3d3170", relief="flat", padx=12, pady=6,
                  command=lambda: self.err(self.refresh_daily)).pack(anchor="w")

    def refresh_daily(self):
        d = api("GET", "/daily", params={"user_id": self.uid})
        self.l_q.config(text="❓ " + d["question"]["text"])
        mine, theirs = d["my_answer"], d["partner_answer"]
        self.l_ans.config(
            text=f'Вы: {mine or "—"}\nПартнёр: {theirs or ("ещё отвечает…" if mine else "—")}')

    def do_answer(self):
        api("POST", "/daily/answer",
            {"user_id": self.uid, "text": self.e_ans.get()})
        self.e_ans.delete(0, "end")
        self.refresh_daily()

    # ---------- Идеи ----------
    def build_ideas(self):
        f = self.tabs["Идеи"]
        self.title(f, "💡 Идеи свиданий")
        tk.Button(f, text="🎲  Мне повезёт!", bg=PINK, fg="white",
                  activebackground="#ff7aa5", font=("", 11, "bold"),
                  relief="flat", padx=12, pady=8,
                  command=lambda: self.err(self.do_lucky)).pack(anchor="w")
        c = self.card(f)
        self.l_idea = tk.Label(c, text="Нажмите кнопку — вытащим идею 🎰",
                               bg=CARD, fg=GOLD, font=("", 12, "bold"),
                               wraplength=460, justify="left")
        self.l_idea.pack(anchor="w")
        self.lb = tk.Listbox(f, width=62, height=12, bg="#0f0b1e", fg=FG,
                             relief="flat", highlightthickness=1,
                             highlightbackground="#3d3170",
                             selectbackground=PINK)
        self.lb.pack(pady=6)
        tk.Button(f, text="🔄  Список", bg="#2d2452", fg=FG,
                  activebackground="#3d3170", relief="flat", padx=12, pady=6,
                  command=lambda: self.err(self.refresh_ideas)).pack(anchor="w")

    def do_lucky(self):
        i = api("GET", "/idea/random")
        self.l_idea.config(text=f'🎲 {i["title"]}\n{i["category"]} • {i["budget"]}')

    def refresh_ideas(self):
        self.lb.delete(0, "end")
        for i in api("GET", "/ideas"):
            mark = "✅" if i["done"] else "🤍"
            self.lb.insert("end", f'{mark}  {i["title"]}  ·  {i["category"]}')

    # ---------- Журнал ----------
    def build_journal(self):
        f = self.tabs["Журнал"]
        self.title(f, "📖 Общий журнал")
        self.e_jt = ttk.Entry(f, width=52); self.e_jt.pack(anchor="w", pady=2)
        self.e_jt.insert(0, "Заголовок момента")
        self.e_jx = ttk.Entry(f, width=52); self.e_jx.pack(anchor="w", pady=2)
        self.e_jx.insert(0, "Что запомнилось?")
        tk.Button(f, text="💾  Сохранить момент", bg=PINK, fg="white",
                  activebackground="#ff7aa5", font=("", 10, "bold"),
                  relief="flat", padx=12, pady=6,
                  command=lambda: self.err(self.do_journal)).pack(anchor="w", pady=4)
        self.lb_j = tk.Listbox(f, width=62, height=13, bg="#0f0b1e", fg=FG,
                               relief="flat", highlightthickness=1,
                               highlightbackground="#3d3170",
                               selectbackground=PINK)
        self.lb_j.pack()

    def do_journal(self):
        api("POST", "/journal", {"user_id": self.uid,
                                 "title": self.e_jt.get(), "text": self.e_jx.get()})
        self.refresh_journal()

    def refresh_journal(self):
        self.lb_j.delete(0, "end")
        for j in api("GET", "/journal", params={"user_id": self.uid}):
            self.lb_j.insert("end", f'💗 {j["title"]} — {j["author"]} ({j["ts"][:10]})')

    # ---------- События ----------
    def build_events(self):
        f = self.tabs["События"]
        self.title(f, "⏳ Обратный отсчёт")
        c = self.card(f)
        self.e_et = ttk.Entry(c, width=30); self.e_et.pack(anchor="w", pady=2)
        self.e_et.insert(0, "Годовщина")
        self.e_ed = ttk.Entry(c, width=15); self.e_ed.pack(anchor="w", pady=2)
        self.e_ed.insert(0, "2027-06-01")
        tk.Button(c, text="➕  Добавить", bg=PINK, fg="white",
                  activebackground="#ff7aa5", font=("", 10, "bold"),
                  relief="flat", padx=12, pady=6,
                  command=lambda: self.err(self.do_event)).pack(anchor="w", pady=4)
        self.lb_e = tk.Listbox(f, width=62, height=11, bg="#0f0b1e", fg=FG,
                               relief="flat", highlightthickness=1,
                               highlightbackground="#3d3170",
                               selectbackground=PINK)
        self.lb_e.pack(pady=4)
        tk.Button(f, text="🔄  Обновить", bg="#2d2452", fg=FG,
                  activebackground="#3d3170", relief="flat", padx=12, pady=6,
                  command=lambda: self.err(self.refresh_events)).pack(anchor="w")

    def do_event(self):
        api("POST", "/events", {"user_id": self.uid,
                                "title": self.e_et.get(), "date": self.e_ed.get()})
        self.refresh_events()

    def refresh_events(self):
        self.lb_e.delete(0, "end")
        for e in api("GET", "/events", params={"user_id": self.uid}):
            left = (f'через {e["days_left"]} дн. ⏳' if e["days_left"] >= 0
                    else f'было {-e["days_left"]} дн. назад 🕰')
            self.lb_e.insert("end", f'🎉 {e["title"]} ({e["date"]}) — {left}')

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
