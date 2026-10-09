import json, os, threading, webbrowser, secrets, urllib.parse, urllib.request, urllib.error, http.server, socketserver, time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME = "Dafan TikTok Control"
API = "https://open.tiktokapis.com"
REDIRECT_URI = "http://127.0.0.1:8765/callback"
SCOPES = "user.info.basic,video.list,video.upload,video.publish"

def request_json(url, method="GET", headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read().decode("utf-8", "replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code}: {detail[:1000]}") from e

class OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        self.server.result = params
        body = b"Authorization received. You can return to Dafan TikTok Control."
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *_):
        pass

class App:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x650")
        self.root.minsize(760, 540)
        self.client_key = ""
        self.client_secret = ""
        self.token = None
        self.user = {}
        self.videos = []
        self.state = tk.StringVar(value="غير متصل")
        self._build()

    def _build(self):
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text=APP_NAME, font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(top, textvariable=self.state).pack(side="right")
        creds = ttk.LabelFrame(self.root, text="إعدادات تطبيق TikTok للمطورين", padding=10)
        creds.pack(fill="x", padx=12, pady=4)
        ttk.Label(creds, text="Client Key").grid(row=0, column=0, sticky="w")
        self.key_entry = ttk.Entry(creds, width=34)
        self.key_entry.grid(row=0, column=1, padx=6, sticky="ew")
        ttk.Label(creds, text="Client Secret").grid(row=0, column=2, sticky="w")
        self.secret_entry = ttk.Entry(creds, width=34, show="*")
        self.secret_entry.grid(row=0, column=3, padx=6, sticky="ew")
        ttk.Button(creds, text="حفظ الإعدادات", command=self.save_config).grid(row=0, column=4, padx=6)
        creds.columnconfigure(1, weight=1); creds.columnconfigure(3, weight=1)

        actions = ttk.Frame(self.root, padding=(12, 6))
        actions.pack(fill="x")
        buttons = [
            ("تسجيل الدخول الرسمي", self.login),
            ("معلومات الحساب", self.load_profile),
            ("فيديوهاتي والإحصائيات", self.load_videos),
            ("رفع فيديو", self.upload_video),
            ("فتح حساب TikTok", self.open_profile),
            ("الإبلاغ عن حساب", self.report_account),
            ("تسجيل الخروج", self.logout),
        ]
        for label, fn in buttons:
            ttk.Button(actions, text=label, command=fn).pack(side="left", padx=3, pady=3)

        info = ttk.LabelFrame(self.root, text="معلومات الحساب", padding=10)
        info.pack(fill="x", padx=12, pady=5)
        self.profile_text = tk.Text(info, height=5, wrap="word")
        self.profile_text.pack(fill="x")
        self.profile_text.insert("1.0", "سجّل الدخول لعرض البيانات التي تسمح بها صلاحيات TikTok الرسمية.")
        self.profile_text.configure(state="disabled")

        frame = ttk.LabelFrame(self.root, text="الفيديوهات والإحصائيات المتاحة", padding=10)
        frame.pack(fill="both", expand=True, padx=12, pady=5)
        cols = ("title", "views", "likes", "comments", "shares", "url")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        names = {"title":"عنوان الفيديو", "views":"مشاهدات", "likes":"إعجابات", "comments":"تعليقات", "shares":"مشاركات", "url":"رابط"}
        widths = {"title":260,"views":75,"likes":75,"comments":75,"shares":75,"url":230}
        for c in cols:
            self.tree.heading(c, text=names[c]); self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.open_selected_video)
        ttk.Label(self.root, text="تنبيه: الوظائف تعتمد على موافقة TikTok والصلاحيات المعتمدة لتطبيقك. لا تدخل كلمة مرورك داخل هذه الأداة.", wraplength=850).pack(fill="x", padx=14, pady=8)
        self.load_config()

    def config_path(self):
        return os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "DafanTikTokControl", "config.json")

    def load_config(self):
        try:
            with open(self.config_path(), "r", encoding="utf-8") as f:
                d = json.load(f)
            self.key_entry.insert(0, d.get("client_key", ""))
            self.secret_entry.insert(0, d.get("client_secret", ""))
        except Exception:
            pass

    def save_config(self):
        key, secret = self.key_entry.get().strip(), self.secret_entry.get().strip()
        if not key or not secret:
            messagebox.showwarning(APP_NAME, "أدخل Client Key وClient Secret من TikTok for Developers.")
            return
        path = self.config_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"client_key": key, "client_secret": secret}, f)
        messagebox.showinfo(APP_NAME, "تم حفظ الإعدادات محلياً. لا تشارك ملف config.json.")

    def creds(self):
        key, secret = self.key_entry.get().strip(), self.secret_entry.get().strip()
        if not key or not secret:
            raise RuntimeError("أدخل Client Key وClient Secret أولاً.")
        return key, secret

    def login(self):
        try:
            key, secret = self.creds()
            state = secrets.token_urlsafe(24)
            params = {"client_key":key, "response_type":"code", "scope":SCOPES, "redirect_uri":REDIRECT_URI, "state":state}
            url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(params)
            server = socketserver.TCPServer(("127.0.0.1", 8765), OAuthHandler)
            server.timeout = 180
            server.result = None
            webbrowser.open(url)
            self.state.set("بانتظار موافقة TikTok…")
            def worker():
                try:
                    end = time.time() + 180
                    while time.time() < end and server.result is None:
                        server.handle_request()
                    result = server.result or {}
                    if "error" in result:
                        raise RuntimeError(str(result))
                    if result.get("state", [""])[0] != state:
                        raise RuntimeError("قيمة state غير مطابقة؛ أُلغيت العملية.")
                    code = result.get("code", [""])[0]
                    if not code: raise RuntimeError("لم يصل رمز التفويض.")
                    payload = urllib.parse.urlencode({"client_key":key, "client_secret":secret, "code":code, "grant_type":"authorization_code", "redirect_uri":REDIRECT_URI}).encode()
                    token_data = request_json("https://open.tiktokapis.com/v2/oauth/token/", "POST", {"Content-Type":"application/x-www-form-urlencoded"}, payload)
                    if token_data.get("error") not in (None, "ok"):
                        raise RuntimeError(str(token_data))
                    self.token = token_data
                    self.root.after(0, lambda: self.state.set("تم تسجيل الدخول"))
                    self.root.after(0, lambda: messagebox.showinfo(APP_NAME, "تم تسجيل الدخول. يمكنك الآن طلب بيانات الحساب."))
                except Exception as e:
                    self.root.after(0, lambda err=str(e): self.fail(err))
                finally:
                    server.server_close()
            threading.Thread(target=worker, daemon=True).start()
        except Exception as e: self.fail(str(e))

    def access_token(self):
        if not self.token or not self.token.get("access_token"):
            raise RuntimeError("سجّل الدخول أولاً.")
        return self.token["access_token"]

    def api_post(self, endpoint, body=None):
        return request_json(API + endpoint, "POST", {"Authorization":"Bearer "+self.access_token(), "Content-Type":"application/json; charset=UTF-8"}, json.dumps(body or {}).encode())

    def load_profile(self):
        def work():
            try:
                d = self.api_post("/v2/user/info/?fields=open_id,display_name,avatar_url,profile_deep_link,bio_description")
                data = d.get("data", {}).get("user", {})
                self.user = data
                text = "\n".join(f"{k}: {v}" for k,v in data.items()) or json.dumps(d, ensure_ascii=False, indent=2)
                self.root.after(0, lambda: self.set_profile(text))
            except Exception as e: self.root.after(0, lambda err=str(e): self.fail(err))
        threading.Thread(target=work, daemon=True).start()

    def set_profile(self, text):
        self.profile_text.configure(state="normal"); self.profile_text.delete("1.0","end"); self.profile_text.insert("1.0",text); self.profile_text.configure(state="disabled")

    def load_videos(self):
        def work():
            try:
                fields = "id,title,video_description,share_url,view_count,like_count,comment_count,share_count,create_time"
                d = self.api_post("/v2/video/list/?fields="+fields, {"max_count":20})
                self.videos = d.get("data", {}).get("videos", d.get("data", {}).get("video_list", []))
                self.root.after(0, self.populate_videos)
            except Exception as e: self.root.after(0, lambda err=str(e): self.fail(err))
        threading.Thread(target=work, daemon=True).start()

    def populate_videos(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for v in self.videos:
            self.tree.insert("", "end", values=(v.get("title") or v.get("video_description",""), v.get("view_count","—"), v.get("like_count","—"), v.get("comment_count","—"), v.get("share_count","—"), v.get("share_url","")))
        if not self.videos:
            messagebox.showinfo(APP_NAME, "لم تُرجع الواجهة أي فيديوهات. تأكد من صلاحية video.list وموافقة التطبيق.")

    def open_selected_video(self, _event=None):
        sel = self.tree.selection()
        if not sel: return
        url = self.tree.item(sel[0], "values")[-1]
        if url: webbrowser.open(url)

    def open_profile(self):
        url = self.user.get("profile_deep_link")
        if not url:
            username = tk.simpledialog.askstring(APP_NAME, "أدخل اسم المستخدم لفتح حسابه (بدون @):")
            if not username: return
            url = "https://www.tiktok.com/@" + urllib.parse.quote(username)
        webbrowser.open(url)

    def report_account(self):
        username = tk.simpledialog.askstring(APP_NAME, "أدخل اسم المستخدم للحساب الذي تريد الإبلاغ عنه (بدون @):")
        if not username: return
        url = "https://www.tiktok.com/@" + urllib.parse.quote(username)
        webbrowser.open(url)
        messagebox.showinfo(APP_NAME, "فتحنا صفحة الحساب. لإرسال البلاغ، استخدم قائمة المشاركة/المزيد داخل TikTok ثم Report / إبلاغ، واختر السبب المناسب. لا توفر واجهة TikTok العامة التي يعتمد عليها هذا المشروع نقطة إرسال بلاغ عن حساب نيابةً عنك.")

    def upload_video(self):
        if not self.token:
            messagebox.showwarning(APP_NAME, "سجّل الدخول أولاً."); return
        path = filedialog.askopenfilename(title="اختر فيديو", filetypes=[("Video files","*.mp4 *.mov *.webm")])
        if not path: return
        messagebox.showinfo(APP_NAME, "سيتم فتح صفحة نشر TikTok. النشر المباشر من API يحتاج موافقة video.publish وتدقيق التطبيق؛ هذه النسخة لا ترسل الفيديو تلقائياً حتى لا توحي بنشر ناجح من دون صلاحية معتمدة.")
        webbrowser.open("https://developers.tiktok.com/products/content-posting-api/")

    def logout(self):
        self.token = None; self.user = {}; self.videos = []
        self.state.set("غير متصل")
        self.set_profile("تم تسجيل الخروج محلياً.")
        for i in self.tree.get_children(): self.tree.delete(i)

    def fail(self, msg):
        self.state.set("حدث خطأ")
        messagebox.showerror(APP_NAME, msg)

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from tkinter import simpledialog
    except Exception:
        pass
    App(root)
    root.mainloop()
