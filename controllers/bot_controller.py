import time
from models.bot_model import SeiBotModel
from views.console_view import ConsoleView

class BotController:
    def __init__(self):
        self.model = SeiBotModel()
        self.view = ConsoleView()
        
    def run(self):
        try:
            print("\n" + "="*50)
            print("    ROBÔ DE ACOMPANHAMENTO ESPECIAL - SEI ")
            print("="*50)
            
            grupo_alvo = input("\n[?] Digite o GRUPO que deseja baixar (Ex: LTS, DEPENDENTE, HORARIO ESPECIAL)\n> ").strip().upper()
            if not grupo_alvo:
                grupo_alvo = "LTS"
                
            print("\n[?] O que você deseja fazer?")
            print("[1] Baixar todas as páginas até o final")
            print("[2] Baixar apenas os processos de um ano específico (e mais recentes)")
            
            opcao = input("\nEscolha a opção (1 ou 2)\n> ").strip()
            
            ano_alvo = None
            if opcao == "2":
                ano_alvo = input("\n[?] Qual ano você quer como limite? (ex: 2026)\n> ").strip()
            
            print("\n" + "="*50)
            self.view.show_message("Iniciando o navegador...")
            # URL de login do SEI Recife fornecida
            initial_url = "https://sip.recife.pe.gov.br/sip/login.php?sigla_orgao_sistema=PR&sigla_sistema=SEI&infra_url=L3NlaS8=" 
            
            self.model.open_initial_page(initial_url)
            
            # Faz o login automático com as credenciais
            self.view.show_message("[PASSO 1] Iniciando login automático...")
            self.model.auto_login("", "", "")
            self.view.show_success("[SUCESSO] Login concluído e possíveis modais fechados!")
            
            # Navega para Acompanhamento Especial pelo menu
            self.view.show_message("[PASSO 2] Navegando para a página Acompanhamento Especial...")
            self.model.navigate_to_acompanhamento()
            time.sleep(2)
            
            # Escolhe o grupo selecionado pelo usuário
            self.view.show_message(f"[PASSO 3] Alterando grupo na tela para '{grupo_alvo}'...")
            self.model.select_group(grupo_alvo)
            
            # Loop de Paginação e Download
            page = 1
            while True:
                self.view.show_message(f"[PASSO 4] Iniciando processamento da página {page}...")
                
                # Se escolheu baixar por ano, verifica as datas antes de baixar
                if ano_alvo:
                    self.view.show_message(f"   -> Verificando se os processos pertencem ao ano {ano_alvo} ou mais recentes...")
                    if self.model.has_passed_target_year(ano_alvo):
                        self.view.show_message(f"   -> Processos anteriores a {ano_alvo} encontrados! Encerrando a busca por limite de ano.")
                        break
                
                self.view.show_message(f"   -> Selecionando todos os itens da página {page}...")
                self.model.select_all_items()
                
                self.view.show_progress(page)
                self.model.click_download_button(page)
                
                self.view.show_message(f"   -> Verificando se existe página {page + 1}...")
                if not self.model.go_to_next_page():
                    self.view.show_message("Não há mais páginas. Fim da lista.")
                    break
                
                page += 1
                
            self.view.show_success("Processo de download finalizado!")
            
        except Exception as e:
            self.view.show_error(str(e))
        finally:
            input("\nPressione Enter no console para fechar o navegador e encerrar o script...")
            self.model.close()
