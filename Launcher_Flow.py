import os
import json
import requests
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import urllib3

# Desabilita avisos de SSL para evitar erros em computadores sem certificados atualizados
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= CONFIGURAÇÕES =================
URL_MANIFESTO = "https://raw.githubusercontent.com/Helder-Leonardo/System-NFe/refs/heads/main/version.json"
URL_BASE_ARQUIVOS = "https://raw.githubusercontent.com/Helder-Leonardo/System-NFe/refs/heads/main/"
PASTA_SISTEMA = r"C:\NFe_Flow_Pro"
ARQUIVO_LOCAL_VERSAO = os.path.join(PASTA_SISTEMA, "version.json")
EXECUTAVEL_FINAL = os.path.join(PASTA_SISTEMA, "main.exe")

class NFeFlowLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NFe Flow Pro - Updater")
        self.root.geometry("400x180")
        self.root.configure(bg="#020617")
        
        tk.Label(self.root, text="VERIFICANDO ATUALIZAÇÕES", font=("Arial", 10, "bold"), bg="#020617", fg="#38BDF8").pack(pady=10)
        
        self.lbl_status = tk.Label(self.root, text="Conectando ao servidor...", bg="#020617", fg="#94A3B8")
        self.lbl_status.pack(pady=5)
        
        self.progress = ttk.Progressbar(self.root, length=300, mode="determinate")
        self.progress.pack(pady=10)

        # Garante que a pasta existe antes de qualquer coisa
        if not os.path.exists(PASTA_SISTEMA):
            os.makedirs(PASTA_SISTEMA)

        self.root.after(500, self.sincronizar)
        self.root.mainloop()

    def sincronizar(self):
        try:
            # 1. Baixa o manifesto do GitHub
            response = requests.get(URL_MANIFESTO, timeout=10, verify=False)
            if response.status_code != 200:
                raise Exception("Não foi possível acessar o servidor de atualização.")
            
            dados_remotos = response.json()
            versao_remota = dados_remotos.get("version", "1.0.0")
            arquivos_necessarios = dados_remotos.get("files", [])

            # 2. Verifica versão local
            versao_local = "0.0.0"
            if os.path.exists(ARQUIVO_LOCAL_VERSAO):
                with open(ARQUIVO_LOCAL_VERSAO, 'r') as f:
                    versao_local = json.load(f).get("version", "0.0.0")

            # 3. Verifica se falta algum arquivo (como o dados_nfe ou o main.exe)
            alguem_faltando = any(not os.path.exists(os.path.join(PASTA_SISTEMA, f)) for f in arquivos_necessarios)

            if versao_remota != versao_local or alguem_faltando:
                self.lbl_status.config(text="Atualizando arquivos do sistema...")
                self.baixar_arquivos(arquivos_necessarios, dados_remotos)
            else:
                self.iniciar_sistema()

        except Exception as e:
            # Se der erro de internet, tenta abrir o que já existe localmente
            if os.path.exists(EXECUTAVEL_FINAL):
                self.iniciar_sistema()
            else:
                messagebox.showerror("Erro", f"Falha na primeira instalação.\nVerifique sua internet.\nErro: {e}")
                self.root.destroy()

    def baixar_arquivos(self, lista, manifesto):
        self.progress["maximum"] = len(lista)
        for i, arquivo in enumerate(lista):
            self.lbl_status.config(text=f"Baixando: {arquivo}")
            self.root.update()
            
            r = requests.get(URL_BASE_ARQUIVOS + arquivo, verify=False)
            if r.status_code == 200:
                with open(os.path.join(PASTA_SISTEMA, arquivo), 'wb') as f:
                    f.write(r.content)
            
            self.progress["value"] = i + 1

        # Salva a nova versão localmente
        with open(ARQUIVO_LOCAL_VERSAO, 'w') as f:
            json.dump(manifesto, f)
        
        self.iniciar_sistema()

    def iniciar_sistema(self):
        self.lbl_status.config(text="Iniciando...")
        self.root.update()
        if os.path.exists(EXECUTAVEL_FINAL):
            # Abre o executável na pasta correta
            subprocess.Popen([EXECUTAVEL_FINAL], cwd=PASTA_SISTEMA)
            self.root.destroy()
        else:
            messagebox.showerror("Erro", "Arquivo principal não encontrado!")
            self.root.destroy()

if __name__ == "__main__":
    NFeFlowLauncher()