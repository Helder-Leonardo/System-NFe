import sys
import os
import re
import time
import threading
import sqlite3
import shutil
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog
from pynput import keyboard
import pyautogui
import pyperclip
import winsound 

# ================= CONFIGURAÇÃO TÉCNICA =================
CAMPO_LEITURA_X, CAMPO_LEITURA_Y = 824, 341 
CAMPO_INSERCAO_X, CAMPO_INSERCAO_Y = 421, 325 
PASTA_SISTEMA = r"C:\NFe_Flow_Pro"
DB_PATH = os.path.join(PASTA_SISTEMA, "dados_nfe.db")
PASTA_BACKUP = os.path.join(PASTA_SISTEMA, "Backups")

os.makedirs(PASTA_SISTEMA, exist_ok=True)
os.makedirs(PASTA_BACKUP, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA journal_mode = WAL')
    cursor.execute('CREATE TABLE IF NOT EXISTS notas (id INTEGER PRIMARY KEY AUTOINCREMENT, chave TEXT UNIQUE, data_bipagem TEXT, status TEXT DEFAULT "PENDENTE")')
    cursor.execute('CREATE TABLE IF NOT EXISTS empresas (cnpj TEXT PRIMARY KEY, nome TEXT NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS usuarios (login TEXT PRIMARY KEY, senha TEXT NOT NULL, nome_exibicao TEXT)')
    cursor.execute("INSERT OR IGNORE INTO usuarios VALUES ('admin', '!Snoopy130499', 'ADMINISTRADOR')")
    conn.commit()
    conn.close()

init_db()
pyautogui.PAUSE = 0.01

# ================= LAUNCHER DE LOGIN =================
class LauncherLogin:
    def __init__(self):
        self.logado = False
        self.user_logado = ""
        self.root = tk.Tk()
        self.root.title("NFe Flow Pro - Autenticação")
        self.root.geometry("400x550")
        self.root.configure(bg="#020617")
        self.root.resizable(False, False)
        
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f'400x550+{int(sw/2-200)}+{int(sh/2-275)}')

        tk.Label(self.root, text="⚡", font=("Inter", 60), bg="#020617", fg="#38BDF8").pack(pady=(40, 5))
        tk.Label(self.root, text="NFe FLOW PRO", font=("Montserrat", 18, "bold"), bg="#020617", fg="#F8FAFC").pack()
        
        f = tk.Frame(self.root, bg="#020617"); f.pack(padx=50, pady=20, fill="x")
        
        tk.Label(f, text="USUÁRIO", font=("Inter", 7, "bold"), bg="#020617", fg="#38BDF8").pack(anchor="w")
        self.ent_user = tk.Entry(f, font=("Inter", 11), bg="#0F172A", fg="white", borderwidth=0, highlightthickness=1, highlightbackground="#1E293B", insertbackground="white")
        self.ent_user.pack(fill="x", pady=(5, 15), ipady=10)
        
        tk.Label(f, text="SENHA", font=("Inter", 7, "bold"), bg="#020617", fg="#38BDF8").pack(anchor="w")
        self.ent_pass = tk.Entry(f, font=("Inter", 11), bg="#0F172A", fg="white", borderwidth=0, highlightthickness=1, highlightbackground="#1E293B", insertbackground="white", show="*")
        self.ent_pass.pack(fill="x", pady=(5, 25), ipady=10)

        tk.Button(self.root, text="ENTRAR", command=self.validar, bg="#38BDF8", fg="#020617", font=("Inter", 10, "bold"), relief="flat", cursor="hand2").pack(padx=50, fill="x", ipady=12)
        
        self.root.bind('<Return>', lambda e: self.validar())
        self.root.mainloop()

    def validar(self):
        u, s = self.ent_user.get(), self.ent_pass.get()
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("SELECT nome_exibicao FROM usuarios WHERE login = ? AND senha = ?", (u, s))
        res = cursor.fetchone(); conn.close()
        if res:
            self.logado = True
            self.user_logado = res[0]
            self.root.destroy()
        else:
            messagebox.showerror("Erro", "Credenciais Inválidas")

# ================= SISTEMA PRINCIPAL =================
class NFeFlowPro:
    def __init__(self, user_name):
        self.root = tk.Tk()
        self.root.title(f"NFe FLOW PRO - Dashboard")
        self.root.geometry("1200x900")
        self.root.configure(bg="#020617")
        
        self.user_atual = user_name
        self.autocopy_rodando = False
        self.processador_rodando = False
        self.menu_visivel = False
        self.gestao_aberta = False
        self.stop_processador = threading.Event()
        self.clipboard_lock = threading.Lock()
        
        self.historico_chaves = set()
        self.lista_checkboxes = []
        self.grupos_widgets = {} 
        self.notas_processadas_sessao = 0
        self.bipadas_sessao = 0

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Vertical.TScrollbar", background="#1E293B", troughcolor="#020617", borderwidth=0)

        self.setup_ui()
        self.carregar_dados_iniciais()
        self.iniciar_listeners()
        self.animar_assinatura()
        self.root.mainloop()

    def setup_ui(self):
        self.header = tk.Frame(self.root, bg="#0F172A", height=70)
        self.header.pack(fill="x")
        self.header.pack_propagate(False) 
        
        self.status_label = tk.Label(self.header, text=f"• SESSÃO ATIVA: {datetime.now().strftime('%d/%m/%Y')} | AGUARDANDO", 
                                   font=("Inter", 9, "bold"), bg="#0F172A", fg="#94A3B8")
        self.status_label.pack(side="left", padx=30)

        if self.user_atual == "ADMINISTRADOR":
            self.btn_gestao_top = tk.Button(self.header, text="⚙️ GESTÃO", command=self.toggle_gestao_menu,
                                           bg="#1E293B", fg="#38BDF8", font=("Inter", 8, "bold"),
                                           relief="flat", padx=15, pady=8, cursor="hand2")
            self.btn_gestao_top.pack(side="right", padx=30)

            self.btn_novo_user_hidden = tk.Button(self.root, text="➕ NOVO OPERADOR", command=self.add_usuario,
                                                 bg="#7C3AED", fg="white", font=("Inter", 8, "bold"),
                                                 relief="flat", cursor="hand2")
            self.btn_novo_user_hidden.place_forget()

        dash = tk.Frame(self.root, bg="#020617", pady=20); dash.pack(fill="x", padx=30)
        self.card_bip = self.criar_card(dash, "BIPADAS HOJE", "#38BDF8")
        self.card_pend = self.criar_card(dash, "AGUARDANDO", "#FACC15")
        self.card_proc = self.criar_card(dash, "PROCESSADAS", "#10B981")

        self.tool_section = tk.Frame(self.root, bg="#020617")
        self.tool_section.pack(fill="x", padx=30, pady=5)

        self.btn_master = tk.Button(self.tool_section, text="⚡ FERRAMENTAS DE CONTROLE", 
                                   command=self.toggle_menu, bg="#1E293B", fg="#38BDF8", 
                                   font=("Inter", 9, "bold"), relief="flat", pady=10, cursor="hand2")
        self.btn_master.pack(fill="x")

        self.container_botoes = tk.Frame(self.tool_section, bg="#0F172A", highlightthickness=1, highlightbackground="#1E293B")
        inner_grid = tk.Frame(self.container_botoes, bg="#0F172A")
        inner_grid.pack(pady=10)
        
        btns = [
            ("☑ TODAS", self.selecionar_todas, "#334155", "#F8FAFC"),
            ("🏢 EMPRESA", self.add_empresa, "#334155", "#F8FAFC"),
            ("🔄 ATUALIZAR", self.atualizar_geral, "#334155", "#F8FAFC"),
            ("🗑️ EXCLUIR", self.excluir_notas, "#450a0a", "#F87171"),
            ("🧹 LIMPAR", self.limpar_contagem_proc, "#334155", "#F8FAFC"),
            ("♻️ REPROCESSAR", self.reprocessar_hoje, "#78350f", "#FBBF24"),
            ("💾 BACKUP", self.fazer_backup, "#064e3b", "#34D399"),
            ("📂 RESTAURAR", self.restaurar_backup, "#1e3a8a", "#93C5FD")
        ]
        for t, c, bg, fg in btns:
            tk.Button(inner_grid, text=t, command=c, bg=bg, fg=fg, font=("Inter", 8, "bold"), 
                      relief="flat", padx=12, pady=6, cursor="hand2").pack(side="left", padx=3)

        search_wrap = tk.Frame(self.root, bg="#020617")
        search_wrap.pack(fill="x", padx=40, pady=(15, 5))
        tk.Label(search_wrap, text="🔍", bg="#020617", fg="#64748B").pack(side="left")
        self.ent_search = tk.Entry(search_wrap, font=("Inter", 11), bg="#020617", fg="#94A3B8", borderwidth=0, insertbackground="white")
        self.ent_search.insert(0, "PESQUISAR EMPRESA...")
        self.ent_search.pack(side="left", fill="x", expand=True, padx=10)
        tk.Frame(self.root, bg="#1E293B", height=1).pack(fill="x", padx=40)

        self.ent_search.bind("<FocusIn>", self._clear_placeholder)
        self.ent_search.bind("<FocusOut>", self._restore_placeholder)
        self.ent_search.bind("<KeyRelease>", self.filtrar_empresas)

        self.list_container = tk.Frame(self.root, bg="#020617")
        self.list_container.pack(fill="both", expand=True, padx=40, pady=10)
        self.canvas = tk.Canvas(self.list_container, bg="#020617", highlightthickness=0)
        self.sb = ttk.Scrollbar(self.list_container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg="#020617")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.sb.pack(side="right", fill="y")

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.root.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        f_footer = tk.Frame(self.root, bg="#0F172A", pady=12); f_footer.pack(fill="x")
        tk.Button(f_footer, text="🔍 BUSCAR NOTA", command=self.buscar_nota, bg="#0891B2", fg="white", font=("Inter", 9, "bold"), relief="flat", padx=20).pack(side="left", padx=40)
        tk.Button(f_footer, text="📂 PASTA RAIZ", command=lambda: os.startfile(PASTA_SISTEMA), bg="#334155", fg="white", font=("Inter", 9, "bold"), relief="flat", padx=20).pack(side="right", padx=40)

        self.frame_ass = tk.Frame(self.root, bg="#020617"); self.frame_ass.pack(pady=10)
        txt = "HELDER LEONARDO HATAKEYAMA MARQUES | CPF: 469.629.338-60"
        self.labels_ass = [tk.Label(self.frame_ass, text=c, font=("Montserrat", 9, "bold"), bg="#020617") for c in txt]
        for l in self.labels_ass: l.pack(side="left")

    def log_gui(self, nfe, chave):
        cnpj = chave[6:20]
        cnpj_f = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        
        if cnpj not in self.grupos_widgets:
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute("SELECT nome FROM empresas WHERE cnpj = ?", (cnpj,))
            res = c.fetchone(); conn.close()
            nome_empresa = res[0] if res else "NÃO CADASTRADA"
            
            f_pai = tk.Frame(self.scroll_frame, bg="#0F172A", highlightthickness=1, highlightbackground="#1E293B", pady=5)
            f_pai.pack(fill="x", pady=5, padx=5)
            f_header = tk.Frame(f_pai, bg="#1E293B"); f_header.pack(fill="x", padx=5)
            
            tk.Label(f_header, text=f"[{cnpj_f}]", bg="#1E293B", fg="#38BDF8", font=("JetBrains Mono", 9, "bold")).pack(side="left", padx=(10, 5))
            tk.Label(f_header, text=nome_empresa, bg="#1E293B", fg="white", font=("Inter", 9, "bold")).pack(side="left")
            
            btn_exp = tk.Button(f_header, text="RECOLHER", command=lambda c=cnpj: self.toggle_grupo(c), bg="#334155", fg="white", font=("Inter", 7), relief="flat", padx=10)
            btn_exp.pack(side="right", padx=10, pady=5)
            lbl_count = tk.Label(f_header, text="0", bg="#38BDF8", fg="#020617", font=("Inter", 8, "bold"), width=3)
            lbl_count.pack(side="right", padx=5)
            
            f_notas = tk.Frame(f_pai, bg="#0F172A"); f_notas.pack(fill="x", padx=10, pady=5)
            self.grupos_widgets[cnpj] = {'frame_pai': f_pai, 'frame_notas': f_notas, 'btn': btn_exp, 'expandido': True, 'count': 0, 'label_count': lbl_count, 'base_text': f"{cnpj_f} {nome_empresa}"}
        
        g = self.grupos_widgets[cnpj]
        g['count'] += 1; g['label_count'].config(text=str(g['count']))
        linha = tk.Frame(g['frame_notas'], bg="#0F172A"); linha.pack(fill="x", pady=1)
        var = tk.BooleanVar(value=True); self.lista_checkboxes.append((var, chave, linha, cnpj))
        tk.Checkbutton(linha, variable=var, bg="#0F172A", selectcolor="#020617").pack(side="left", padx=5)
        tk.Label(linha, text=f"NF {nfe}", fg="#F1F5F9", bg="#0F172A", font=("JetBrains Mono", 9, "bold"), width=12, anchor="w").pack(side="left")
        tk.Label(linha, text=chave, fg="#475569", bg="#0F172A", font=("JetBrains Mono", 8)).pack(side="left", padx=10)
        self.atualizar_cards()

    def buscar_nota(self):
        t = simpledialog.askstring("Buscar", "NF ou Chave:")
        if not t: 
            return
        for v, ch, l, cp in self.lista_checkboxes:
            if t in ch or t in ch[25:34]:
                y = l.winfo_rooty() - self.scroll_frame.winfo_rooty()
                self.canvas.yview_moveto(y / self.scroll_frame.winfo_height())
                l.configure(bg="#1E293B")
                self.root.after(1000, lambda: l.configure(bg="#0F172A"))
                break

    # --- Métodos de Controle ---
    def toggle_menu(self):
        if self.menu_visivel:
            self.container_botoes.pack_forget()
            self.btn_master.config(text="⚡ FERRAMENTAS DE CONTROLE", bg="#1E293B")
        else:
            self.container_botoes.pack(fill="x", pady=2)
            self.btn_master.config(text="▲ RECOLHER FERRAMENTAS", bg="#334155")
        self.menu_visivel = not self.menu_visivel
        self.root.update_idletasks()

    def toggle_gestao_menu(self):
        if self.gestao_aberta:
            self.btn_novo_user_hidden.place_forget()
            self.btn_gestao_top.config(bg="#1E293B")
        else:
            x = self.btn_gestao_top.winfo_rootx() - self.root.winfo_rootx()
            self.btn_novo_user_hidden.place(x=x, y=70, width=150)
            self.btn_novo_user_hidden.lift()
            self.btn_gestao_top.config(bg="#334155")
        self.gestao_aberta = not self.gestao_aberta

    def criar_card(self, p, l, c):
        f = tk.Frame(p, bg="#0F172A", highlightthickness=1, highlightbackground="#1E293B", padx=20, pady=15)
        f.pack(side="left", expand=True, padx=10)
        tk.Label(f, text=l, font=("Inter", 7, "bold"), bg="#0F172A", fg="#64748B").pack()
        v = tk.Label(f, text="0", font=("JetBrains Mono", 22, "bold"), bg="#0F172A", fg=c)
        v.pack()
        return v

    def _clear_placeholder(self, e):
        if self.ent_search.get() == "PESQUISAR EMPRESA...":
            self.ent_search.delete(0, tk.END)
            self.ent_search.config(fg="white")

    def _restore_placeholder(self, e):
        if not self.ent_search.get():
            self.ent_search.insert(0, "PESQUISAR EMPRESA...")
            self.ent_search.config(fg="#94A3B8")

    def processador_loop(self):
        self.processador_rodando = True
        self.status_label.config(text="• STATUS: PROCESSANDO...", fg="#38BDF8")
        notas = [i for i in self.lista_checkboxes if i[0].get()]
        for var, chave, linha, cnpj in notas:
            if self.stop_processador.is_set(): break
            with self.clipboard_lock:
                pyautogui.click(CAMPO_INSERCAO_X, CAMPO_INSERCAO_Y)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.press("backspace")
                pyperclip.copy(chave)
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "v")
                pyautogui.press("enter")
                time.sleep(0.3)
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("UPDATE notas SET status = 'PROCESSADA' WHERE chave = ?", (chave,))
            conn.commit()
            conn.close()
            self.notas_processadas_sessao += 1
            self.root.after(0, lambda v=var, l=linha: [v.set(False), l.configure(bg="#064e3b")])
            self.atualizar_cards()
        self.processador_rodando = False
        self.status_label.config(text="• STATUS: CONCLUÍDO", fg="#10B981")

    def on_press(self, key):
        try:
            if key == keyboard.Key.f7:
                self.autocopy_rodando = True
                self.status_label.config(text="• SESSÃO: MONITORANDO", fg="#10B981")
            elif key == keyboard.Key.f8:
                self.autocopy_rodando = False
                self.status_label.config(text="• SESSÃO: PAUSADO", fg="#F87171")
            elif key == keyboard.Key.f9 and not self.processador_rodando:
                self.stop_processador.clear()
                threading.Thread(target=self.processador_loop, daemon=True).start()
            elif key == keyboard.Key.f10:
                self.stop_processador.set()
                winsound.Beep(600, 200)
            elif key == keyboard.Key.enter and self.autocopy_rodando:
                threading.Thread(target=self.executar_bipagem, daemon=True).start()
        except: pass

    def iniciar_listeners(self):
        keyboard.Listener(on_press=self.on_press, daemon=True).start()

    def carregar_dados_iniciais(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        hoje = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT chave, status FROM notas WHERE data_bipagem = ?", (hoje,))
        for ch, st in c.fetchall():
            self.historico_chaves.add(ch)
            self.bipadas_sessao += 1
            if st == 'PENDENTE':
                self.log_gui(ch[25:34], ch)
            else:
                self.notas_processadas_sessao += 1
        conn.close()
        self.atualizar_cards()

    def add_usuario(self):
        l = simpledialog.askstring("Novo", "Login:")
        s = simpledialog.askstring("Senha", "Senha:", show="*")
        if l and s:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO usuarios VALUES (?,?,?)", (l, s, l.upper()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Sucesso", "Cadastrado!")
            self.toggle_gestao_menu()

    def add_empresa(self):
        c = simpledialog.askstring("CNPJ", "Números:")
        n = simpledialog.askstring("Nome", "Empresa:")
        if c and n:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO empresas VALUES (?,?)", (c, n.upper()))
            conn.commit()
            conn.close()
            self.atualizar_geral()

    def animar_assinatura(self, p=0):
        cores = [(56, 189, 248), (192, 132, 252), (244, 114, 182)]
        for i, lbl in enumerate(self.labels_ass):
            idx = (p + i) % 30
            c1, c2 = cores[idx // 10 % 3], cores[(idx // 10 + 1) % 3]
            f = (idx % 10) / 10.0
            hex_c = f'#{int(c1[0]+(c2[0]-c1[0])*f):02x}{int(c1[1]+(c2[1]-c1[1])*f):02x}{int(c1[2]+(c2[2]-c1[2])*f):02x}'
            lbl.config(fg=hex_c)
        self.root.after(50, lambda: self.animar_assinatura(p + 1))

    def filtrar_empresas(self, e=None):
        t = self.ent_search.get().upper()
        if t == "PESQUISAR EMPRESA...": return
        for cnpj, info in self.grupos_widgets.items():
            if t in info['base_text'].upper():
                info['frame_pai'].pack(fill="x", pady=5, padx=5)
            else:
                info['frame_pai'].pack_forget()

    def toggle_grupo(self, cnpj):
        g = self.grupos_widgets[cnpj]
        if g['expandido']:
            g['frame_notas'].pack_forget()
            g['btn'].config(text="EXPANDIR")
        else:
            g['frame_notas'].pack(fill="x", padx=10, pady=5)
            g['btn'].config(text="RECOLHER")
        g['expandido'] = not g['expandido']

    def selecionar_todas(self):
        est = not all(v.get() for v,c,l,cp in self.lista_checkboxes)
        for v,c,l,cp in self.lista_checkboxes:
            v.set(est)
        self.atualizar_cards()

    def atualizar_cards(self):
        self.card_bip.config(text=str(self.bipadas_sessao))
        self.card_pend.config(text=str(sum(1 for v,c,l,cp in self.lista_checkboxes if v.get())))
        self.card_proc.config(text=str(self.notas_processadas_sessao))

    def atualizar_geral(self):
        for w in self.scroll_frame.winfo_children(): w.destroy()
        self.lista_checkboxes.clear()
        self.historico_chaves.clear()
        self.grupos_widgets.clear()
        self.bipadas_sessao = 0
        self.notas_processadas_sessao = 0
        self.carregar_dados_iniciais()

    def limpar_contagem_proc(self):
        self.notas_processadas_sessao = 0
        self.atualizar_cards()

    def fazer_backup(self):
        dest = os.path.join(PASTA_BACKUP, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(DB_PATH, dest)
        messagebox.showinfo("Backup", "Salvo!")

    def restaurar_backup(self):
        arq = filedialog.askopenfilename(initialdir=PASTA_BACKUP, filetypes=(("DB", "*.db"),))
        if arq and messagebox.askyesno("Confirmar", "Restaurar?"):
            shutil.copy2(arq, DB_PATH)
            self.atualizar_geral()

    def reprocessar_hoje(self):
        if messagebox.askyesno("Confirmar", "Reprocessar hoje?"):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("UPDATE notas SET status = 'PENDENTE' WHERE data_bipagem = ?", (datetime.now().strftime("%Y-%m-%d"),))
            conn.commit()
            conn.close()
            self.atualizar_geral()

    def excluir_notas(self):
        sel = [i for i in self.lista_checkboxes if i[0].get()]
        if sel and messagebox.askyesno("Confirmar", f"Excluir {len(sel)}?"):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            for v, ch, l, cp in sel:
                c.execute("DELETE FROM notas WHERE chave = ?", (ch,))
            conn.commit()
            conn.close()
            self.atualizar_geral()

    def executar_bipagem(self):
        with self.clipboard_lock:
            pyperclip.copy("")
            pyautogui.click(CAMPO_LEITURA_X, CAMPO_LEITURA_Y)
            pyautogui.hotkey("ctrl", "a", "c")
            time.sleep(0.2)
            txt = re.sub(r"\D", "", pyperclip.paste().strip())
            
            if len(txt) in [44, 48]:
                # NOVA LÓGICA DE DUPLICIDADE COM ALERTA
                if txt in self.historico_chaves:
                    winsound.Beep(1000, 800)
                    
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("SELECT data_bipagem, status FROM notas WHERE chave = ?", (txt,))
                    res = c.fetchone()
                    conn.close()
                    
                    info_ext = ""
                    if res:
                        info_ext = f"\nData de Registro: {res[0]}\nStatus no Sistema: {res[1]}"
                    
                    messagebox.showwarning(
                        "NOTA DUPLICADA", 
                        f"⚠️ ESTA NOTA JÁ FOI BIPADA!\n\n"
                        f"NF: {txt[25:34]}\n"
                        f"CHAVE: {txt}{info_ext}"
                    )
                    return

                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO notas (chave, data_bipagem) VALUES (?,?)", (txt, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    self.historico_chaves.add(txt)
                    self.bipadas_sessao += 1
                    self.root.after(0, lambda: self.log_gui(txt[25:34], txt))
                    winsound.Beep(1500, 150)
                except: pass
                finally: conn.close()

if __name__ == "__main__":
    launcher = LauncherLogin()
    if launcher.logado:
        NFeFlowPro(launcher.user_logado)