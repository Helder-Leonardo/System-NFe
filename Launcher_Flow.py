import os
import sys
import json
import time
import requests
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# ================= CONFIGURAÇÕES DE ATUALIZAÇÃO =================
# Se usar GitHub, a URL deve ser a versão "Raw" do arquivo
URL_MANIFESTO = "https://raw.githubusercontent.com/Helder-Leonardo/System-NFe/refs/heads/main/version.json"
URL_BASE_ARQUIVOS = "https://raw.githubusercontent.com/Helder-Leonardo/System-NFe/refs/heads/main/main.py"
PASTA_SISTEMA = r"C:\Users\Windows\Desktop\SystemNFe"
ARQUIVO_LOCAL_VERSAO = os.path.join(PASTA_SISTEMA, "version.json")
EXECUTAVEL_FINAL = os.path.join(PASTA_SISTEMA, "main.py") # Pode ser .exe se você compilar

class NFeFlowLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NFe Flow Pro - Sincronizador")
        self.root.geometry("450x200")
        self.root.configure(bg="#020617")
        self.root.resizable(False, False)

        # Estilo da Progressbar
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", thickness=10, troughcolor="#0F172A", background="#38BDF8", bordercolor="#020617")

        tk.Label(self.root, text="⚡", font=("Inter", 30), bg="#020617", fg="#38BDF8").pack(pady=(10, 0))
        tk.Label(self.root, text="NFe FLOW PRO", font=("Montserrat", 12, "bold"), bg="#020617", fg="#F8FAFC").pack()
        
        self.lbl_status = tk.Label(self.root, text="Iniciando verificação...", font=("Inter", 9), bg="#020617", fg="#94A3B8")
        self.lbl_status.pack(pady=10)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=350, mode="determinate")
        self.progress.pack(pady=5)

        os.makedirs(PASTA_SISTEMA, exist_ok=True)
        
        # Inicia a lógica em background para não travar a janela
        self.root.after(500, self.checar_atualizacoes)
        self.root.mainloop()

    def checar_atualizacoes(self):
        try:
            # 1. Tenta baixar o manifesto do servidor
            response = requests.get(URL_MANIFESTO, timeout=10)
            if response.status_code != 200:
                raise Exception("Servidor de atualizações offline.")
            
            dados_remotos = response.json()
            versao_remota = dados_remotos.get("version", "1.0.0")
            arquivos_necessarios = dados_remotos.get("files", [])

            # 2. Verifica versão local
            versao_local = "0.0.0"
            if os.path.exists(ARQUIVO_LOCAL_VERSAO):
                with open(ARQUIVO_LOCAL_VERSAO, 'r') as f:
                    versao_local = json.load(f).get("version", "0.0.0")

            # 3. Verifica se falta algum arquivo físico ou se a versão mudou
            falta_arquivo = any(not os.path.exists(os.path.join(PASTA_SISTEMA, f)) for f in arquivos_necessarios)

            if versao_remota != versao_local or falta_arquivo:
                self.lbl_status.config(text=f"Nova versão encontrada: {versao_remota}. Baixando...", fg="#38BDF8")
                self.baixar_pacotes(arquivos_necessarios, dados_remotos)
            else:
                self.lbl_status.config(text="Sistema atualizado!", fg="#10B981")
                self.root.after(1000, self.finalizar_e_abrir)

        except Exception as e:
            messagebox.showwarning("Modo Offline", f"Não foi possível conectar ao servidor.\nIniciando versão local...\nErro: {e}")
            self.finalizar_e_abrir()

    def baixar_pacotes(self, lista_arquivos, manifesto_completo):
        self.progress["maximum"] = len(lista_arquivos)
        
        for i, arquivo in enumerate(lista_arquivos):
            self.lbl_status.config(text=f"Baixando: {arquivo}...")
            self.root.update()
            
            url_download = URL_BASE_ARQUIVOS + arquivo
            caminho_destino = os.path.join(PASTA_SISTEMA, arquivo)
            
            # Garante que as subpastas existam
            os.makedirs(os.path.dirname(caminho_destino), exist_ok=True)
            
            # Download do arquivo
            try:
                r = requests.get(url_download, stream=True)
                if r.status_code == 200:
                    with open(caminho_destino, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                
                self.progress["value"] = i + 1
            except:
                messagebox.showerror("Erro", f"Erro ao baixar {arquivo}")
                return

        # Atualiza o manifesto local após sucesso
        with open(ARQUIVO_LOCAL_VERSAO, 'w') as f:
            json.dump(manifesto_completo, f)
        
        self.lbl_status.config(text="Atualização concluída!", fg="#10B981")
        self.root.after(1000, self.finalizar_e_abrir)

    def finalizar_e_abrir(self):
        if os.path.exists(EXECUTAVEL_FINAL):
            # Inicia o seu código original
            subprocess.Popen([sys.executable, EXECUTAVEL_FINAL], cwd=PASTA_SISTEMA)
            self.root.destroy()
        else:
            messagebox.showerror("Erro", "Arquivo principal não encontrado mesmo após atualização!")
            self.root.destroy()

if __name__ == "__main__":
    NFeFlowLauncher()