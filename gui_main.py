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
        self.geometry("800x600")
        
        self.tarefas = []
        
        # Grid layout (2 rows, 2 columns)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # =========================================================
        # FRAME ESQUERDO: Login e Ações
        # =========================================================
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.left_frame, text="Credenciais do SEI", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.entry_user = ctk.CTkEntry(self.left_frame, placeholder_text="Usuário (ex: ticiano.filho)", width=250)
        self.entry_user.pack(pady=5)
        
        self.entry_pass = ctk.CTkEntry(self.left_frame, placeholder_text="Senha", show="*", width=250)
        self.entry_pass.pack(pady=5)
        
        self.combo_orgao = ctk.CTkComboBox(self.left_frame, values=["SEDUC", "SAD", "GRB", "OUTRO"], width=250)
        self.combo_orgao.set("SEDUC")
        self.combo_orgao.pack(pady=5)

        ctk.CTkLabel(self.left_frame, text="Configuração de Download", font=("Arial", 16, "bold")).pack(pady=(20, 10))

        self.combo_grupo = ctk.CTkComboBox(self.left_frame, values=["LTS", "DEPENDENTE", "HORARIO ESPECIAL", "DESAVERBAÇÃO"], width=250)
        self.combo_grupo.set("LTS")
        self.combo_grupo.pack(pady=5)

        self.entry_ano = ctk.CTkEntry(self.left_frame, placeholder_text="Ano Limite (Vazio = Todas)", width=250)
        self.entry_ano.pack(pady=5)

        self.btn_add_task = ctk.CTkButton(self.left_frame, text="Adicionar à Lista", command=self.adicionar_tarefa, fg_color="green", hover_color="darkgreen")
        self.btn_add_task.pack(pady=10)

        self.check_csv_var = ctk.StringVar(value="S")
        self.check_csv = ctk.CTkCheckBox(self.left_frame, text="Gerar CSV ao final e exibir Quantitativos?", variable=self.check_csv_var, onvalue="S", offvalue="N")
        self.check_csv.pack(pady=10)

        # Aviso sobre não mexer no chrome
        warning_label = ctk.CTkLabel(self.left_frame, text="⚠️ IMPORTANTE: Não mexa no mouse nem\nfeche o Chrome enquanto o robô estiver rodando!", text_color="#FF6B6B", font=("Arial", 12, "bold"))
        warning_label.pack(pady=5)

        self.btn_start = ctk.CTkButton(self.left_frame, text="INICIAR ROBÔ", font=("Arial", 14, "bold"), command=self.iniciar_robo)
        self.btn_start.pack(pady=10)
        
        self.btn_stop = ctk.CTkButton(self.left_frame, text="PARAR ROBÔ", font=("Arial", 14, "bold"), command=self.parar_robo, fg_color="#C0392B", hover_color="#922B21", state="disabled")
        self.btn_stop.pack(pady=5)
        
        self.btn_analise = ctk.CTkButton(self.left_frame, text="Apenas Extrair Dados (Sem Baixar)", command=self.iniciar_analise_apenas, fg_color="gray", hover_color="darkgray")
        self.btn_analise.pack(pady=10)

        # Evento de parada
        self.stop_event = threading.Event()

        # =========================================================
        # FRAME DIREITO: Progresso e Logs
        # =========================================================
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(self.right_frame, text="Fila de Tarefas", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.lista_tarefas_box = ctk.CTkTextbox(self.right_frame, height=100, state="disabled")
        self.lista_tarefas_box.pack(padx=10, pady=5, fill="x")

        ctk.CTkButton(self.right_frame, text="Limpar Lista", command=self.limpar_tarefas, width=100).pack(pady=5)

        ctk.CTkLabel(self.right_frame, text="Progresso (Logs)", font=("Arial", 16, "bold")).pack(pady=(10, 10))
        
        self.log_box = ctk.CTkTextbox(self.right_frame, state="disabled")
        self.log_box.pack(padx=10, pady=5, fill="both", expand=True)

    def append_log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def adicionar_tarefa(self):
        grupo = self.combo_grupo.get().strip().upper()
        ano = self.entry_ano.get().strip()
        
        if grupo:
            self.tarefas.append({"grupo": grupo, "ano": ano})
            
            # Atualiza listbox
            self.lista_tarefas_box.configure(state="normal")
            limite_texto = f" (até {ano})" if ano else " (todas)"
            self.lista_tarefas_box.insert("end", f"- {grupo}{limite_texto}\n")
            self.lista_tarefas_box.configure(state="disabled")
            
            # Limpa campo
            self.entry_ano.delete(0, 'end')

    def limpar_tarefas(self):
        self.tarefas = []
        self.lista_tarefas_box.configure(state="normal")
        self.lista_tarefas_box.delete("1.0", "end")
        self.lista_tarefas_box.configure(state="disabled")

    def parar_robo(self):
        self.append_log("\n[!] Solicitando parada do robô... Aguarde.\n")
        self.stop_event.set()
        self.btn_stop.configure(state="disabled")

    def iniciar_robo(self):
        user = self.entry_user.get().strip()
        pwd = self.entry_pass.get().strip()
        orgao = self.combo_orgao.get().strip()
        fazer_csv = self.check_csv_var.get()

        if not self.tarefas:
            self.append_log("[-] Adicione pelo menos uma tarefa na lista!\n")
            return

        self.stop_event.clear()
        self.btn_start.configure(state="disabled")
        self.btn_analise.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        
        self.append_log("\n" + "="*40 + "\n[*] INICIANDO AUTOMAÇÃO\n" + "="*40 + "\n")

        # Inicia a thread para não travar a GUI
        t = threading.Thread(target=self._run_bot_thread, args=(user, pwd, orgao, "download", self.tarefas, fazer_csv))
        t.start()

    def iniciar_analise_apenas(self):
        self.stop_event.clear()
        self.append_log("\n" + "="*40 + "\n[*] INICIANDO APENAS EXTRAÇÃO DE DADOS\n" + "="*40 + "\n")
        self.btn_start.configure(state="disabled")
        self.btn_analise.configure(state="disabled")
        
        t = threading.Thread(target=self._run_bot_thread, args=("", "", "", "analise", [], "N"))
        t.start()

    def _run_bot_thread(self, user, pwd, orgao, opcao, tarefas, fazer_csv):
        # Cria a view para a GUI (com o callback para o log_box)
        gui_view = GuiView(self.append_log)
        controller = BotController(view=gui_view)
        
        # Roda o processo passando a função que checa se o usuário clicou em Parar
        controller.run_gui(user, pwd, orgao, opcao, tarefas, fazer_csv, check_stop=lambda: self.stop_event.is_set())
        
        # Reativa botões via thread segura
        self.after(0, lambda: self.btn_start.configure(state="normal"))
        self.after(0, lambda: self.btn_analise.configure(state="normal"))
        self.after(0, lambda: self.btn_stop.configure(state="disabled"))

if __name__ == "__main__":
    app = AppGUI()
    app.mainloop()
