class ConsoleView:
    def show_message(self, message):
        print(f"[*] {message}")
        
    def show_progress(self, page_number):
        print(f"[>] Realizando download da página {page_number}...")
        
    def show_success(self, message):
        print(f"[+] {message}")

    def show_error(self, message):
        print(f"[-] Erro: {message}")
