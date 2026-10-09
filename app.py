import json, os, threading, webbrowser, secrets, urllib.parse, urllib.request, urllib.error, http.server, socketserver, time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

APP_NAME = "Dafan TikTok Control"
API = "https://open.tiktokapis.com"
REDIRECT_URI = "http://127.0.0.1:8765/callback"
SCOPES = "user.info.basic,video.list"

BG = "#0b1020"
PANEL = "#131b2e"
PANEL2 = "#1b2740"
ACCENT = "#25f4ee"
PINK = "#fe2c55"
TEXT = "#f4f7ff"
MUTED = "#a9b5ce"

def request_json(url, method="GET", headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read().decode("utf-8", "replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code}: {detail[:900]}") from e

class OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        self.server.result = urllib.parse.parse_qs(parsed.query)
        body = b"Authorization received. Return to Dafan TikTok Control."
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *_): pass

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1020x720")
        self.root.minsize(860, 620)
        self.root.configure(bg=BG)
        self.token = None
        self.user = {}
        self.videos = []
        self.state = tk.StringVar(value="غير متصل")
        self._style()
        self._build()

    def _style(self):
        s = ttk.Style()
        try: s.theme_use("clam")
        except Exception: pass
        s.configure("Treeview", background=PANEL, foreground=TEXT, fieldbackground=PANEL, rowheight=30, borderwidth=0)
        s.configure("Treeview.Heading", background=PANEL2, foreground=ACCENT, font=("Segoe UI", 10, "bold"), relief="flat")
        s.map("Treeview", background=[("selected", "#263a5f")], foreground=[("selected", TEXT)])

    def config_path(self):
        return os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "DafanTikTokControl", "config.json")

    def _build(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=24, pady=(20,10))
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")
        tk.Label(brand, text="دفان", bg=BG, fg=ACCENT, font=("Segoe UI", 30, "bold")).pack(anchor="w")
        tk.Label(brand, text="DAFAN  •  TIKTOK CONTROL", bg=BG, fg=MUTED, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        right = tk.Frame(header, bg=PANEL, padx=14, pady=10)
        right.pack(side="right")
        tk.Label(right, text="حالة الاتصال", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=(0,10))
        tk.Label(right, textvariable=self.state, bg=PANEL, fg=ACCENT, font=("Segoe UI", 10, "bold")).pack(side="left")

        # Decorative watermark banner
        banner = tk.Frame(self.root, bg=PANEL2, height=82)
        banner.pack(fill="x", padx=24, pady=5)
        banner.pack_propagate(False)
        tk.Label(banner, text="دفــــان", bg=PANEL2, fg="#eaf4ff", font=("Segoe UI", 25, "bold")).pack(side="right", padx=22)
        tk.Label(banner, text="لوحة إدارة آمنة باستخدام واجهات TikTok الرسمية", bg=PANEL2, fg=MUTED, font=("Segoe UI", 12)).pack(side="left", padx=22)

        credentials = tk.Frame(self.root, bg=PANEL, padx=14, pady=12)
        credentials.pack(fill="x", padx=24, pady=10)
        tk.Label(credentials, text="إعداد التطبيق", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).grid(row=0,column=0,columnspan=4,sticky="w",pady=(0,8))
        tk.Label(credentials, text="Client Key", bg=PANEL, fg=MUTED).grid(row=1,column=0,sticky="w")
        self.key_entry = tk.Entry(credentials, bg="#0d1526", fg=TEXT, insertbackground=TEXT, relief="flat", font=("Consolas",10))
        self.key_entry.grid(row=2,column=0,sticky="ew",padx=(0,12),ipady=7)
        tk.Label(credentials, text="Client Secret", bg=PANEL, fg=MUTED).grid(row=1,column=1,sticky="w")
        self.secret_entry = tk.Entry(credentials, bg="#0d1526", fg=TEXT, insertbackground=TEXT, show="*", relief="flat", font=("Consolas",10))
        self.secret_entry.grid(row=2,column=1,sticky="ew",padx=(0,12),ipady=7)
        self._button(credentials, "حفظ الإعدادات", self.save_config, ACCENT, "#07131a").grid(row=2,column=2,padx=4)
        self._button(credentials, "دليل المطورين", lambda:webbrowser.open("https://developers.tiktok.com/"), PINK, "white").grid(row=2,column=3,padx=4)
        credentials.columnconfigure(0,weight=1); credentials.columnconfigure(1,weight=1)

        actions = tk.Frame(self.root, bg=BG)
        actions.pack(fill="x", padx=24, pady=(2,10))
        buttons = [
            ("🔐  تسجيل الدخول", self.login, ACCENT, "#07131a"),
            ("👤  معلومات الحساب", self.load_profile, PANEL2, TEXT),
            ("📊  الفيديوهات والإحصائيات", self.load_videos, PANEL2, TEXT),
            ("⬆  رفع فيديو", self.upload_video, PANEL2, TEXT),
            ("🚩  إعداد بلاغ", self.report_account, PINK, "white"),
            ("🌐  فتح TikTok", self.open_profile, PANEL2, TEXT),
            ("خروج", self.logout, "#3a2031", "white"),
        ]
        for label,fn,bg,fg in buttons:
            self._button(actions,label,fn,bg,fg).pack(side="left", padx=(0,6), pady=3, ipady=5)

        lower = tk.Frame(self.root, bg=BG)
        lower.pack(fill="both", expand=True, padx=24, pady=(0,10))
        left = tk.Frame(lower, bg=PANEL, padx=12, pady=12)
        left.pack(side="left", fill="both", expand=True, padx=(0,8))
        tk.Label(left, text="معلومات الحساب", bg=PANEL, fg=ACCENT, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0,8))
        self.profile_text = tk.Text(left, height=7, bg="#0d1526", fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=("Consolas",10))
        self.profile_text.pack(fill="both", expand=True)
        self.profile_text.insert("1.0", "سجّل الدخول لعرض المعلومات المتاحة حسب صلاحيات التطبيق.")
        self.profile_text.configure(state="disabled")
        right = tk.Frame(lower, bg=PANEL, padx=12, pady=12)
        right.pack(side="left", fill="both", expand=True, padx=(8,0))
        tk.Label(right, text="فيديوهاتي والإحصائيات", bg=PANEL, fg=ACCENT, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0,8))
        cols=("title","views","likes","comments")
        self.tree=ttk.Treeview(right,columns=cols,show="headings")
        for c,t,w in [("title","عنوان الفيديو",270),("views","مشاهدات",80),("likes","إعجابات",80),("comments","تعليقات",80)]:
            self.tree.heading(c,text=t); self.tree.column(c,width=w,anchor="w")
        self.tree.pack(fill="both",expand=True)
        self.tree.bind("<Double-1>",self.open_selected_video)
        footer=tk.Label(self.root,text="نسخة تجريبية • الوظائف تتطلب موافقة وصلاحيات TikTok الرسمية • لا تدخل كلمة مرورك هنا",bg=BG,fg=MUTED,font=("Segoe UI",9))
        footer.pack(pady=(0,12))
        self.load_config()

    def _button(self,parent,text,command,bg,fg):
        return tk.Button(parent,text=text,command=command,bg=bg,fg=fg,activebackground=ACCENT,activeforeground="#07131a",relief="flat",bd=0,cursor="hand2",font=("Segoe UI",9,"bold"),padx=10,pady=8)

    def load_config(self):
        try:
            with open(self.config_path(),"r",encoding="utf-8") as f: d=json.load(f)
            self.key_entry.insert(0,d.get("client_key","")); self.secret_entry.insert(0,d.get("client_secret",""))
        except Exception: pass

    def save_config(self):
        key,secret=self.key_entry.get().strip(),self.secret_entry.get().strip()
        if not key or not secret:
            messagebox.showwarning(APP_NAME,"أدخل Client Key وClient Secret من بوابة المطورين."); return
        path=self.config_path(); os.makedirs(os.path.dirname(path),exist_ok=True)
        with open(path,"w",encoding="utf-8") as f: json.dump({"client_key":key,"client_secret":secret},f)
        messagebox.showinfo(APP_NAME,"حُفظت الإعدادات محلياً. لا تشارك ملف config.json.")

    def creds(self):
        key,secret=self.key_entry.get().strip(),self.secret_entry.get().strip()
        if not key or not secret: raise RuntimeError("أدخل Client Key وClient Secret أولاً.")
        return key,secret

    def login(self):
        try:
            key,secret=self.creds()
            state=secrets.token_urlsafe(24)
            params={"client_key":key,"response_type":"code","scope":SCOPES,"redirect_uri":REDIRECT_URI,"state":state}
            url="https://www.tiktok.com/v2/auth/authorize/?"+urllib.parse.urlencode(params)
            server=socketserver.TCPServer(("127.0.0.1",8765),OAuthHandler); server.timeout=180; server.result=None
            webbrowser.open(url); self.state.set("بانتظار الموافقة…")
            def worker():
                try:
                    end=time.time()+180
                    while time.time()<end and server.result is None: server.handle_request()
                    result=server.result or {}
                    if result.get("state",[""])[0]!=state: raise RuntimeError("تعذر التحقق من state أو انتهت المهلة.")
                    code=result.get("code",[""])[0]
                    if not code: raise RuntimeError("لم يصل رمز التفويض.")
                    payload=urllib.parse.urlencode({"client_key":key,"client_secret":secret,"code":code,"grant_type":"authorization_code","redirect_uri":REDIRECT_URI}).encode()
                    token_data=request_json("https://open.tiktokapis.com/v2/oauth/token/","POST",{"Content-Type":"application/x-www-form-urlencoded"},payload)
                    if token_data.get("error") not in (None,"ok"): raise RuntimeError(str(token_data))
                    self.token=token_data
                    self.root.after(0,lambda:self.state.set("متصل"))
                    self.root.after(0,lambda:messagebox.showinfo(APP_NAME,"تم تسجيل الدخول الرسمي."))
                except Exception as e: self.root.after(0,lambda err=str(e):self.fail(err))
                finally: server.server_close()
            threading.Thread(target=worker,daemon=True).start()
        except Exception as e: self.fail(str(e))

    def access_token(self):
        if not self.token or not self.token.get("access_token"): raise RuntimeError("سجّل الدخول أولاً.")
        return self.token["access_token"]

    def api_post(self,endpoint,body=None):
        return request_json(API+endpoint,"POST",{"Authorization":"Bearer "+self.access_token(),"Content-Type":"application/json; charset=UTF-8"},json.dumps(body or {}).encode())

    def load_profile(self):
        def work():
            try:
                d=self.api_post("/v2/user/info/?fields=open_id,display_name,avatar_url,profile_deep_link,bio_description")
                data=d.get("data",{}).get("user",{}); self.user=data
                out="\n".join(f"{k}: {v}" for k,v in data.items()) or json.dumps(d,ensure_ascii=False,indent=2)
                self.root.after(0,lambda:self.set_profile(out))
            except Exception as e: self.root.after(0,lambda err=str(e):self.fail(err))
        threading.Thread(target=work,daemon=True).start()

    def set_profile(self,text):
        self.profile_text.configure(state="normal"); self.profile_text.delete("1.0","end"); self.profile_text.insert("1.0",text); self.profile_text.configure(state="disabled")

    def load_videos(self):
        def work():
            try:
                fields="id,title,video_description,share_url,view_count,like_count,comment_count,share_count"
                d=self.api_post("/v2/video/list/?fields="+fields,{"max_count":20})
                self.videos=d.get("data",{}).get("videos",[])
                self.root.after(0,self.populate_videos)
            except Exception as e: self.root.after(0,lambda err=str(e):self.fail(err))
        threading.Thread(target=work,daemon=True).start()

    def populate_videos(self):
        for x in self.tree.get_children(): self.tree.delete(x)
        for v in self.videos:
            self.tree.insert("","end",values=(v.get("title") or v.get("video_description",""),v.get("view_count","—"),v.get("like_count","—"),v.get("comment_count","—")))
        if not self.videos: messagebox.showinfo(APP_NAME,"لا توجد فيديوهات معادة. تحقق من صلاحية video.list وموافقة التطبيق.")

    def open_selected_video(self,_event=None):
        sel=self.tree.selection()
        if not sel: return
        idx=self.tree.index(sel[0])
        if idx < len(self.videos) and self.videos[idx].get("share_url"): webbrowser.open(self.videos[idx]["share_url"])

    def open_profile(self):
        url=self.user.get("profile_deep_link")
        if not url:
            username=simpledialog.askstring(APP_NAME,"اسم المستخدم (بدون @):")
            if not username:return
            url="https://www.tiktok.com/@"+urllib.parse.quote(username)
        webbrowser.open(url)

    def report_account(self):
        win=tk.Toplevel(self.root); win.title("إعداد بلاغ — دفان"); win.geometry("500x430"); win.configure(bg=BG); win.transient(self.root)
        tk.Label(win,text="إعداد بلاغ",bg=BG,fg=PINK,font=("Segoe UI",20,"bold")).pack(anchor="w",padx=20,pady=(18,4))
        tk.Label(win,text="اكتب اسم الحساب والسبب والتفاصيل. هذه الشاشة تحفظ نص البلاغ أو تنسخه فقط؛ لا توجد واجهة رسمية عامة لإرسال بلاغ الحساب مباشرة من التطبيق.",bg=BG,fg=MUTED,wraplength=450,justify="left").pack(anchor="w",padx=20,pady=8)
        tk.Label(win,text="اسم الحساب (بدون @)",bg=BG,fg=TEXT).pack(anchor="w",padx=20)
        name=tk.Entry(win,bg=PANEL,fg=TEXT,insertbackground=TEXT,relief="flat"); name.pack(fill="x",padx=20,pady=5,ipady=7)
        tk.Label(win,text="سبب البلاغ",bg=BG,fg=TEXT).pack(anchor="w",padx=20)
        reason=ttk.Combobox(win,values=["انتحال شخصية","مضايقة أو تنمّر","محتوى ضار","احتيال أو تضليل","محتوى غير مناسب","سبب آخر"],state="readonly")
        reason.pack(fill="x",padx=20,pady=5); reason.set("اختر السبب")
        tk.Label(win,text="تفاصيل واقعية تدعم البلاغ",bg=BG,fg=TEXT).pack(anchor="w",padx=20)
        details=tk.Text(win,height=5,bg=PANEL,fg=TEXT,insertbackground=TEXT,relief="flat"); details.pack(fill="both",expand=True,padx=20,pady=5)
        def copy_report():
            if not name.get().strip() or reason.get()=="اختر السبب":
                messagebox.showwarning(APP_NAME,"أدخل اسم الحساب واختر السبب.",parent=win); return
            report=f"الحساب: @{name.get().strip().lstrip('@')}\\nالسبب: {reason.get()}\\nالتفاصيل: {details.get('1.0','end').strip()}"
            self.root.clipboard_clear(); self.root.clipboard_append(report)
            messagebox.showinfo(APP_NAME,"تم نسخ نص البلاغ. لم يُرسل إلى TikTok؛ يمكنك حفظه أو استخدامه عند الإبلاغ عبر TikTok.",parent=win)
        self._button(win,"نسخ نص البلاغ",copy_report,PINK,"white").pack(anchor="e",padx=20,pady=14)

    def upload_video(self):
        if not self.token: messagebox.showwarning(APP_NAME,"سجّل الدخول أولاً."); return
        path=filedialog.askopenfilename(title="اختر فيديو",filetypes=[("Video","*.mp4 *.mov *.webm")])
        if not path:return
        messagebox.showinfo(APP_NAME,"هذه النسخة لا تنشر تلقائياً. النشر الرسمي يحتاج موافقة video.publish، واتباع واجهة الموافقة والخصوصية المطلوبة من TikTok.")

    def logout(self):
        self.token=None; self.user={}; self.videos=[]; self.state.set("غير متصل")
        self.set_profile("تم تسجيل الخروج محلياً.")
        for x in self.tree.get_children(): self.tree.delete(x)

    def fail(self,msg):
        self.state.set("خطأ")
        messagebox.showerror(APP_NAME,msg)

if __name__=="__main__":
    root=tk.Tk()
    App(root)
    root.mainloop()
