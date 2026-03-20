import os
import sys
import platform
import socket
import wmi
import subprocess
import uuid
import csv 
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from collections import Counter
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

#Aparência
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class CheckMachinePro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CheckMachine Pro - WJ Tech")
        self.geometry("1350x850")
        
        load_dotenv(".env")
        self.supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        self.c_local = wmi.WMI()
        self.lista_empresas_cache = []
        self.admin_password = "Senha.Exemplo"

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(expand=True, fill="both")

        self.show_home()

    def clear_screen(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

    def show_home(self):
        self.clear_screen()
        ctk.CTkLabel(self.main_container, text="CheckMachine", font=("Arial", 40, "bold")).pack(pady=(100, 5))
        ctk.CTkLabel(self.main_container, text="Desenvolvido por Wendell Junior", font=("Arial", 10)).pack(pady=(0, 50))
        btn_width = 280
        ctk.CTkButton(self.main_container, text="Coletar Informações", width=btn_width, height=45, command=self.show_coletor).pack(pady=10)
        ctk.CTkButton(self.main_container, text="Acessar Informações", width=btn_width, height=45, command=self.show_acesso_leitura).pack(pady=10)
        ctk.CTkButton(self.main_container, text="Configurações", width=btn_width, height=45, fg_color="#3d3d3d", command=self.auth_config).pack(pady=10)

    def auth_config(self):
        auth_win = ctk.CTkToplevel(self)
        auth_win.title("Acesso Restrito")
        auth_win.geometry("350x220")
        auth_win.grab_set()
        auth_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 175
        y = self.winfo_y() + (self.winfo_height() // 2) - 110
        auth_win.geometry(f"+{x}+{y}")
        ctk.CTkLabel(auth_win, text="Senha de Administrador:", font=("Arial", 14, "bold")).pack(pady=(25, 10))
        password_entry = ctk.CTkEntry(auth_win, show="*", width=220)
        password_entry.pack(pady=5)
        password_entry.focus_set()
        def verificar(event=None):
            if password_entry.get() == self.admin_password:
                auth_win.destroy()
                self.show_config()
            else:
                messagebox.showerror("Erro", "Senha incorreta!")
                password_entry.delete(0, 'end')
        ctk.CTkButton(auth_win, text="Entrar", command=verificar).pack(pady=25)
        auth_win.bind('<Return>', verificar)

    def show_coletor(self):
        self.clear_screen()
        self.get_empresas_db()
        ctk.CTkButton(self.main_container, text="← Voltar", width=80, command=self.show_home).pack(anchor="nw", padx=20, pady=20)
        options_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        options_frame.pack(pady=5)
        self.var_servidor = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(options_frame, text="Servidor Remoto?", variable=self.var_servidor, command=self.toggle_servidor_fields).pack(side="left", padx=20)
        self.form_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.form_frame.pack(pady=10)
        self.sel_empresa = ctk.CTkOptionMenu(self.form_frame, values=self.lista_empresas_cache if self.lista_empresas_cache else ["Cadastre uma empresa"], width=350)
        self.sel_empresa.pack(pady=5)
        self.sel_origem = ctk.CTkOptionMenu(self.form_frame, values=["Itech", "Terceiros", "Cliente"], width=350)
        self.sel_origem.pack(pady=5)
        self.ent_usuario = ctk.CTkEntry(self.form_frame, placeholder_text="Usuário (Pessoa)", width=350)
        self.ent_usuario.pack(pady=5)
        self.ent_srv_ip = ctk.CTkEntry(self.form_frame, placeholder_text="IP do Servidor", width=350)
        self.ent_srv_user = ctk.CTkEntry(self.form_frame, placeholder_text="Admin User", width=350)
        self.ent_srv_pass = ctk.CTkEntry(self.form_frame, placeholder_text="Senha do Servidor", show="*", width=350)
        self.ent_setor = ctk.CTkEntry(self.form_frame, placeholder_text="Setor", width=350)
        self.ent_setor.pack(pady=5)
        self.ent_tombo = ctk.CTkEntry(self.form_frame, placeholder_text="Tombo", width=350)
        self.ent_tombo.pack(pady=5)
        ctk.CTkButton(self.main_container, text="INICIAR COLETA E ENVIAR", fg_color="#1a73e8", font=("Arial", 14, "bold"), height=45, command=self.executar_coleta).pack(pady=20)

    def toggle_servidor_fields(self):
        if self.var_servidor.get():
            self.ent_usuario.pack_forget()
            self.ent_srv_ip.pack(pady=5, after=self.sel_origem)
            self.ent_srv_user.pack(pady=5, after=self.ent_srv_ip)
            self.ent_srv_pass.pack(pady=5, after=self.ent_srv_user)
        else:
            self.ent_srv_ip.pack_forget(); self.ent_srv_user.pack_forget(); self.ent_srv_pass.pack_forget()
            self.ent_usuario.pack(pady=5, after=self.sel_origem)

    def verificar_bitdefender(self, wmi_obj):
        try:
            processos = [p.Name.lower() for p in wmi_obj.Win32_Process(name="vsserv.exe")]
            processos += [p.Name.lower() for p in wmi_obj.Win32_Process(name="bdagent.exe")]
            if processos: return "Sim"
            servicos = wmi_obj.Win32_Service(Name="EPSecurityService")
            if servicos: return "Sim"
            return "Não"
        except: return "Não"

    def executar_coleta(self):
        try:
            if self.var_servidor.get():
                ip, user, pw = self.ent_srv_ip.get(), self.ent_srv_user.get(), self.ent_srv_pass.get()
                c = wmi.WMI(computer=ip, user=user, password=pw)
                user_display = "SERVIDOR_REMOTO"
            else:
                c = self.c_local
                user_display = self.ent_usuario.get()
            sys_os = c.Win32_OperatingSystem()[0]
            caps = [f"{int(m.Capacity)/(1024**3):.0f}GB" for m in c.Win32_PhysicalMemory()]
            net = c.Win32_NetworkAdapterConfiguration(IPEnabled=True)[0]
            bitdefender_status = self.verificar_bitdefender(c)
            payload = {
                "MAC": net.MACAddress, "PC_Name": sys_os.CSName, "Empresa": self.sel_empresa.get(), "User": user_display,
                "OS": sys_os.Caption.replace('Microsoft ', ''), "CPU": c.Win32_Processor()[0].Name.strip(),
                "RAM": " | ".join([f"{q}: {c}" for c, q in Counter(caps).items()]),
                "Storage": " | ".join([f"{d.Model.strip()} ({int(d.Size)/(1024**3):.0f}GB)" for d in c.Win32_DiskDrive() if not d.InterfaceType or "USB" not in d.InterfaceType.upper()]),
                "MotherBoard": f"{c.Win32_BaseBoard()[0].Manufacturer} {c.Win32_BaseBoard()[0].Product}",
                "IP": net.IPAddress[0], "Setor": self.ent_setor.get(), "Tombo": self.ent_tombo.get(),
                "Origem": self.sel_origem.get(), "Dominio": c.Win32_ComputerSystem()[0].Domain,
                "BitDefender": bitdefender_status
            }
            self.supabase.table("maquinas").upsert(payload, on_conflict="MAC").execute()
            self.dialogo_finalizacao()
        except Exception as e: messagebox.showerror("Erro", f"Falha na operação: {e}")

    def dialogo_finalizacao(self):
        final_win = ctk.CTkToplevel(self)
        final_win.title("Envio Concluído")
        final_win.geometry("400x250")
        final_win.grab_set()
        final_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 125
        final_win.geometry(f"+{x}+{y}")
        ctk.CTkLabel(final_win, text="Envio realizado com sucesso!", font=("Arial", 16, "bold")).pack(pady=20)
        ctk.CTkLabel(final_win, text="O que deseja fazer agora?", font=("Arial", 12)).pack(pady=5)
        def voltar(): final_win.destroy(); self.show_home()
        def fechar_e_apagar():
            if messagebox.askyesno("Confirmar", "Apagar pasta do app permanentemente?"): self.suicidio_do_app()
        ctk.CTkButton(final_win, text="Voltar ao CheckMachine", command=voltar, width=250).pack(pady=10)
        ctk.CTkButton(final_win, text="Fechar e Apagar Pasta", fg_color="#c0392b", command=fechar_e_apagar, width=250).pack(pady=10)

    def suicidio_do_app(self):
        app_path = os.path.abspath(sys.argv[0])
        cmd = f'timeout /t 2 > nul && rd /s /q "{os.path.dirname(app_path)}"'
        subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        self.destroy(); sys.exit()

    def get_empresas_db(self):
        try:
            res = self.supabase.table("lista_empresas").select("nome_empresa").execute()
            self.lista_empresas_cache = [r['nome_empresa'] for r in res.data]
        except: self.lista_empresas_cache = []

    def show_acesso_leitura(self):
        self.clear_screen()
        self.get_empresas_db()
        header = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(header, text="← Voltar", width=80, command=self.show_home).pack(side="left")
        ctk.CTkLabel(header, text="Filtrar Empresa:").pack(side="left", padx=(30, 5))
        opcoes = ["Todas"] + self.lista_empresas_cache
        self.sel_filtro_leitura = ctk.CTkOptionMenu(header, values=opcoes, command=lambda e: self.atualizar_tabela(self.tree_leitura, filtro=e))
        self.sel_filtro_leitura.pack(side="left", padx=5)
        ctk.CTkButton(header, text="Exportar CSV", fg_color="#27ae60", command=self.exportar_csv_otimizado).pack(side="right")
        self.tree_leitura = self.create_treeview(self.main_container)
        self.atualizar_tabela(self.tree_leitura)

    def create_treeview(self, parent):
        self.cols = ("MAC", "PC_Name", "Empresa", "Setor", "User", "OS", "RAM", "CPU", "Storage", "IP", "MotherBoard", "Origem", "BitDefender")
        tree = ttk.Treeview(parent, columns=self.cols, show="headings")
        h_scroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=h_scroll.set)
        for c in self.cols: tree.heading(c, text=c); tree.column(c, width=130, anchor="center")
        tree.pack(expand=True, fill="both", padx=20); h_scroll.pack(fill="x", padx=20, pady=(0, 20))
        return tree

    def atualizar_tabela(self, tree, filtro=None):
        for i in tree.get_children(): tree.delete(i)
        query = self.supabase.table("maquinas").select("*")
        if filtro and filtro != "Todas": query = query.eq("Empresa", filtro)
        dados = query.execute().data
        for r in dados: tree.insert("", "end", values=[r.get(c) for c in self.cols])

    #EXPORTAR CSV
    def exportar_csv_otimizado(self):
        filas = [self.tree_leitura.item(c)["values"] for c in self.tree_leitura.get_children()]
        if not filas: return
        f = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if f:
            try:
                with open(f, mode='w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow(self.cols) # Cabeçalhos
                    writer.writerows(filas) # Dados
                messagebox.showinfo("Sucesso", "CSV exportado com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro ao exportar", str(e))

    def show_config(self):
        self.clear_screen()
        ctk.CTkButton(self.main_container, text="← Voltar", width=80, command=self.show_home).pack(anchor="nw", padx=20, pady=20)
        ctk.CTkLabel(self.main_container, text="Painel Admin", font=("Arial", 22, "bold")).pack(pady=20)
        ctk.CTkButton(self.main_container, text="Empresas", width=350, height=45, command=self.show_gerenciar_empresas).pack(pady=10)
        ctk.CTkButton(self.main_container, text="Itens (Máquinas)", width=350, height=45, fg_color="#c0392b", command=self.show_admin_dados).pack(pady=10)

    def show_admin_dados(self):
        self.clear_screen()
        self.get_empresas_db()
        ctk.CTkButton(self.main_container, text="← Voltar", width=80, command=self.show_config).pack(anchor="nw", padx=20, pady=10)
        filter_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(filter_frame, text="Filtrar Itens por Empresa:").pack(side="left", padx=5)
        opcoes_admin = ["Todas"] + self.lista_empresas_cache
        self.sel_filtro_admin = ctk.CTkOptionMenu(filter_frame, values=opcoes_admin, command=lambda e: self.atualizar_tabela(self.tree_admin, filtro=e))
        self.sel_filtro_admin.pack(side="left", padx=5)
        btn_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(btn_frame, text="+ Novo Item", fg_color="green", command=lambda: self.abrir_formulario()).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Editar Selecionado", command=lambda: self.abrir_formulario(self.tree_admin)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Excluir", fg_color="red", command=lambda: self.excluir(self.tree_admin)).pack(side="right", padx=5)
        self.tree_admin = self.create_treeview(self.main_container)
        self.atualizar_tabela(self.tree_admin)

    def abrir_formulario(self, tree=None):
        dados_atuais = {}; is_edit = False
        if tree and tree.selection():
            is_edit = True
            valores = tree.item(tree.selection()[0])['values']
            dados_atuais = dict(zip(self.cols, valores))
        form_win = ctk.CTkToplevel(self)
        form_win.title("Formulário de Item")
        form_win.geometry("500x700")
        form_win.grab_set()
        scroll_frame = ctk.CTkScrollableFrame(form_win, width=450, height=600)
        scroll_frame.pack(pady=10, padx=10, fill="both", expand=True)
        entries = {}
        for col in self.cols:
            ctk.CTkLabel(scroll_frame, text=col).pack(pady=(5, 0))
            ent = ctk.CTkEntry(scroll_frame, width=300)
            if is_edit: ent.insert(0, dados_atuais.get(col, ""))
            if col == "MAC" and is_edit: ent.configure(state="disabled")
            ent.pack(pady=5); entries[col] = ent
        def salvar():
            payload = {c: entries[c].get() for c in self.cols}
            try:
                self.supabase.table("maquinas").upsert(payload, on_conflict="MAC").execute()
                messagebox.showinfo("Sucesso", "Dados salvos!"); form_win.destroy(); self.atualizar_tabela(self.tree_admin)
            except Exception as e: messagebox.showerror("Erro", str(e))
        ctk.CTkButton(form_win, text="SALVAR", command=salvar).pack(pady=10)

    def show_gerenciar_empresas(self):
        self.clear_screen()
        ctk.CTkButton(self.main_container, text="← Voltar", width=80, command=self.show_config).pack(anchor="nw", padx=20, pady=20)
        self.ent_nova = ctk.CTkEntry(self.main_container, width=300); self.ent_nova.pack()
        ctk.CTkButton(self.main_container, text="Add", command=self.add_emp_db).pack(pady=5)
        self.lb_emp = tk.Listbox(self.main_container, bg="#1d1d1d", fg="white", border=0); self.lb_emp.pack(fill="both", expand=True, padx=100)
        self.atualizar_lb()
        ctk.CTkButton(self.main_container, text="Remover", fg_color="red", command=self.rem_emp_db).pack(pady=20)

    def add_emp_db(self):
        if self.ent_nova.get(): self.supabase.table("lista_empresas").insert({"nome_empresa": self.ent_nova.get()}).execute(); self.atualizar_lb()

    def rem_emp_db(self):
        s = self.lb_emp.curselection()
        if s: self.supabase.table("lista_empresas").delete().eq("nome_empresa", self.lb_emp.get(s)).execute(); self.atualizar_lb()

    def atualizar_lb(self):
        self.lb_emp.delete(0, tk.END); self.get_empresas_db()
        for e in self.lista_empresas_cache: self.lb_emp.insert(tk.END, e)

    def excluir(self, tree):
        s = tree.selection()
        if s:
            mac = tree.item(s[0])['values'][0]
            if messagebox.askyesno("Confirma?", f"Excluir {mac}?"):
                self.supabase.table("maquinas").delete().eq("MAC", mac).execute(); self.atualizar_tabela(tree)

if __name__ == "__main__":
    app = CheckMachinePro()
    app.mainloop()
