import customtkinter as ctk
import threading
from views.gui_view import GuiView
from controllers.bot_controller import BotController

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SEI Bot - Acompanhamento Especial")
        self.geometry("900x650")
        self.tarefas = []
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # =========================================================
        # FRAME ESQUERDO: Login e Ações
        # =========================================================
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.left_frame, text="Credenciais do SEI", font=("Arial", 16, "bold")).pack(pady=5)
        self.entry_user = ctk.CTkEntry(self.left_frame, placeholder_text="Usuário (ex: ticiano.filho)", width=250)
        self.entry_user.pack(pady=2)
        self.entry_pass = ctk.CTkEntry(self.left_frame, placeholder_text="Senha", show="*", width=250)
        self.entry_pass.pack(pady=2)
        self.combo_orgao = ctk.CTkComboBox(self.left_frame, values=["SEDUC", "SAD", "GRB", "OUTRO"], width=250)
        self.combo_orgao.set("SEDUC")
        self.combo_orgao.pack(pady=2)

        ctk.CTkLabel(self.left_frame, text="Configuração de Download", font=("Arial", 16, "bold")).pack(pady=(15, 5))

        # Lista de opções corrigida
        self.processos_opcoes = [
            "TODOS", "ABONO PERMANENCIA", "ANOTAÇÃO", "APOSENTADORIA", "APOSENTADORIA POR INVALIDEZ", 
            "AULA ATIVIDADE", "AUXÍLIO FUNERAL", "AVERBAÇÃO", "CARGA HORÁRIA", "CASAMENTO", "CAT", 
            "CERTIDÃO/DECLARAÇÃO", "CREDENCIAMENTO", "CTC", "DECLARAÇÃO DE VÍNCULO", "DEPENDENTE", 
            "DESAVERBAÇÃO", "DESLIGAMENTOS", "DIFÍCIL ACESSO", "ENQUADRAMENTO ADI", 
            "FICHA FINANCEIRA / FICHA FUNCIONAL", "GOZO DE FÉRIAS", "HORA EXTRA", "HORARIO ESPECIAL", 
            "INSALUBRIDADE", "ISENÇÃO DE IMPOSTO DE RENDA", "LDPF", "LICENÇA LUTO", "LICENÇA MATERNIDADE", 
            "LICENÇA MATERNIDADE POR ADOÇÃO", "LICENÇA PARA CASAMENTO", "LICENÇA PARA TRATO DE INTERRESSE PARTICULAR", 
            "LICENÇA PATERNIDADE", "LICENÇA PRÊMIO", "LTS", "MUDANÇA DE NIVEL", "PROGRESSÃO/TITULAÇÃO", 
            "READAPTAÇÃO", "RECONSIDERAÇÃO DE ACRESCIMO", "RECONSIDERAÇÃO DE DESPACHO", "REDUÇÃO DE ATIVIDADES", 
            "REINTEGRAÇÃO", "REQUERIMENTO", "RESTOS DEIXADOS", "REVISÃO DE VENCIMENTOS", "SALÁRIO FAMÍLIA", 
            "VALE ALIMENTAÇÃO"
        ]
        self.combo_grupo = ctk.CTkComboBox(self.left_frame, values=self.processos_opcoes, width=250)
        self.combo_grupo.set("TODOS")
        self.combo_grupo.pack(pady=2)

        self.radio_filtro_var = ctk.IntVar(value=0)
        filtros_frame = ctk.CTkFrame(self.left_frame)
        filtros_frame.pack(pady=5)
        
        ctk.CTkRadioButton(filtros_frame, text="S/ Filtro", variable=self.radio_filtro_var, value=0, command=self._toggle_filtro).grid(row=0, column=0, padx=5)
        ctk.CTkRadioButton(filtros_frame, text="Ano", variable=self.radio_filtro_var, value=1, command=self._toggle_filtro).grid(row=0, column=1, padx=5)
        ctk.CTkRadioButton(filtros_frame, text="Mês/Ano", variable=self.radio_filtro_var, value=2, command=self._toggle_filtro).grid(row=0, column=2, padx=5)
        ctk.CTkRadioButton(filtros_frame, text="Data", variable=self.radio_filtro_var, value=3, command=self._toggle_filtro).grid(row=0, column=3, padx=5)

        self.entry_filtro = ctk.CTkEntry(self.left_frame, placeholder_text="Sem filtro", width=250, state="disabled")
        self.entry_filtro.pack(pady=5)

        self.btn_add_task = ctk.CTkButton(self.left_frame, text="Adicionar à Lista", command=self.adicionar_tarefa, fg_color="green", hover_color="darkgreen")
        self.btn_add_task.pack(pady=5)

        self.check_csv_var = ctk.StringVar(value="S")
        self.check_csv = ctk.CTkCheckBox(self.left_frame, text="Gerar CSV ao final?", variable=self.check_csv_var, onvalue="S", offvalue="N")
        self.check_csv.pack(pady=5)
        
        self.check_renomear_var = ctk.StringVar(value="N")
        self.check_renomear = ctk.CTkCheckBox(self.left_frame, text="Renomear PDFs antigos?", variable=self.check_renomear_var, onvalue="S", offvalue="N")
        self.check_renomear.pack(pady=5)

        # Ações
        acoes_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        acoes_frame.pack(pady=10)
        
        self.btn_start = ctk.CTkButton(acoes_frame, text="INICIAR DOWNLOADS", font=("Arial", 12, "bold"), command=self.iniciar_robo)
        self.btn_start.grid(row=0, column=0, padx=5, pady=5)
        
        self.btn_analise = ctk.CTkButton(acoes_frame, text="SÓ EXTRAIR CSV", command=self.iniciar_analise_apenas, fg_color="gray", hover_color="darkgray")
        self.btn_analise.grid(row=0, column=1, padx=5, pady=5)
        
        self.btn_renomear = ctk.CTkButton(acoes_frame, text="SÓ RENOMEAR", command=self.iniciar_renomear_apenas, fg_color="#F39C12", hover_color="#D68910")
        self.btn_renomear.grid(row=1, column=0, padx=5, pady=5)
        
        self.btn_stop = ctk.CTkButton(acoes_frame, text="PARAR ROBÔ", font=("Arial", 12, "bold"), command=self.parar_robo, fg_color="#C0392B", hover_color="#922B21", state="disabled")
        self.btn_stop.grid(row=1, column=1, padx=5, pady=5)

        self.stop_event = threading.Event()

        # =========================================================
        # FRAME DIREITO: Progresso e Logs
        # =========================================================
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(self.right_frame, text="Fila de Tarefas", font=("Arial", 16, "bold")).pack(pady=5)
        self.lista_tarefas_box = ctk.CTkTextbox(self.right_frame, height=100, state="disabled")
        self.lista_tarefas_box.pack(padx=10, pady=2, fill="x")
        ctk.CTkButton(self.right_frame, text="Limpar Lista", command=self.limpar_tarefas, width=100).pack(pady=2)

        ctk.CTkLabel(self.right_frame, text="Progresso (Logs)", font=("Arial", 16, "bold")).pack(pady=(10, 5))
        self.log_box = ctk.CTkTextbox(self.right_frame, state="disabled")
        self.log_box.pack(padx=10, pady=2, fill="both", expand=True)

    def _toggle_filtro(self):
        val = self.radio_filtro_var.get()
        self.entry_filtro.configure(state="normal")
        self.entry_filtro.delete(0, 'end')
        if val == 0:
            self.entry_filtro.configure(placeholder_text="Sem filtro", state="disabled")
        elif val == 1:
            self.entry_filtro.configure(placeholder_text="Ano (ex: 2026)")
        elif val == 2:
            self.entry_filtro.configure(placeholder_text="Mês/Ano (ex: 01/2026)")
        elif val == 3:
            self.entry_filtro.configure(placeholder_text="Data (ex: 08/01/2026)")

    def append_log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def adicionar_tarefa(self):
        grupo = self.combo_grupo.get().strip().upper()
        filtro_val = self.radio_filtro_var.get()
        filtro_texto = self.entry_filtro.get().strip()
        
        ano, mes, data = None, None, None
        if filtro_val == 1: ano = filtro_texto
        elif filtro_val == 2: mes = filtro_texto
        elif filtro_val == 3: data = filtro_texto
        
        limite_texto = ""
        if ano: limite_texto = f" (Ano: {ano})"
        elif mes: limite_texto = f" (Mês: {mes})"
        elif data: limite_texto = f" (Data: {data})"

        def _add(g):
            if not any(t["grupo"] == g and t.get("ano") == ano and t.get("mes") == mes and t.get("data") == data for t in self.tarefas):
                self.tarefas.append({"grupo": g, "ano": ano, "mes": mes, "data": data})
                self.lista_tarefas_box.configure(state="normal")
                self.lista_tarefas_box.insert("end", f"- {g}{limite_texto}\n")
                self.lista_tarefas_box.configure(state="disabled")

        if grupo == "TODOS":
            processos = [p.upper() for p in self.processos_opcoes if p != "TODOS"]
            for p in processos: _add(p)
            self.entry_filtro.delete(0, 'end')
        elif grupo:
            _add(grupo)
            self.entry_filtro.delete(0, 'end')

    def limpar_tarefas(self):
        self.tarefas = []
        self.lista_tarefas_box.configure(state="normal")
        self.lista_tarefas_box.delete("1.0", "end")
        self.lista_tarefas_box.configure(state="disabled")

    def parar_robo(self):
        self.append_log("\n[!] Solicitando parada do robô... Aguarde.\n")
        self.stop_event.set()
        self.btn_stop.configure(state="disabled")

    def _prepare_run(self, mode):
        if not self.tarefas:
            self.append_log("[-] Adicione pelo menos uma tarefa na lista!\n")
            return False
        self.stop_event.clear()
        self.btn_start.configure(state="disabled")
        self.btn_analise.configure(state="disabled")
        self.btn_renomear.configure(state="disabled")
        if mode == "download": self.btn_stop.configure(state="normal")
        return True

    def iniciar_robo(self):
        if not self._prepare_run("download"): return
        self.append_log("\n" + "="*40 + "\n[*] INICIANDO AUTOMAÇÃO\n" + "="*40 + "\n")
        t = threading.Thread(target=self._run_bot_thread, args=(
            self.entry_user.get().strip(), self.entry_pass.get().strip(), self.combo_orgao.get().strip(), 
            "download", self.tarefas, self.check_csv_var.get(), self.check_renomear_var.get() == "S"
        ))
        t.start()

    def iniciar_analise_apenas(self):
        if not self._prepare_run("analise"): return
        self.append_log("\n" + "="*40 + "\n[*] INICIANDO APENAS EXTRAÇÃO DE DADOS\n" + "="*40 + "\n")
        t = threading.Thread(target=self._run_bot_thread, args=("", "", "", "analise", self.tarefas, "N", self.check_renomear_var.get() == "S"))
        t.start()
        
    def iniciar_renomear_apenas(self):
        if not self._prepare_run("renomear"): return
        self.append_log("\n" + "="*40 + "\n[*] INICIANDO APENAS RENOMEAÇÃO DE PDFs\n" + "="*40 + "\n")
        t = threading.Thread(target=self._run_bot_thread, args=("", "", "", "renomear", self.tarefas, "N", True))
        t.start()

    def _run_bot_thread(self, user, pwd, orgao, opcao, tarefas, fazer_csv, renomear_pdfs):
        gui_view = GuiView(self.append_log)
        controller = BotController(view=gui_view)
        controller.run_gui(user, pwd, orgao, opcao, tarefas, fazer_csv, renomear_pdfs, check_stop=lambda: self.stop_event.is_set())
        
        self.after(0, lambda: self.btn_start.configure(state="normal"))
        self.after(0, lambda: self.btn_analise.configure(state="normal"))
        self.after(0, lambda: self.btn_renomear.configure(state="normal"))
        self.after(0, lambda: self.btn_stop.configure(state="disabled"))

if __name__ == "__main__":
    app = AppGUI()
    app.mainloop()
