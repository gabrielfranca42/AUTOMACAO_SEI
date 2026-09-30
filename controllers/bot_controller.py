import time
import os
from models.bot_model import SeiBotModel
from views.console_view import ConsoleView

class BotController:
    def __init__(self, view=None):
        self.model = SeiBotModel()
        self.view = view if view else ConsoleView()

    def coletar_tarefas(self):
        """Coleta a lista de grupos e anos do usuário antes de abrir o navegador."""
        tarefas = []

        print("\n" + "="*60)
        print("       ROBÔ DE ACOMPANHAMENTO ESPECIAL - SEI")
        print("="*60)

        print("\n[?] O que você deseja fazer?")
        print("[1] Baixar todas as páginas até o final")
        print("[2] Baixar apenas os processos de um ano específico")
        print("[3] Analisar PDFs baixados (extrair para CSV)")

        opcao = input("\nEscolha a opção (1, 2 ou 3)\n> ").strip()

        if opcao == "3":
            return "analise", []

        while True:
            print("\n" + "-"*40)
            grupo = input("[?] Digite o GRUPO que deseja baixar (Ex: LTS, DEPENDENTE, HORARIO ESPECIAL)\n> ").strip().upper()
            if not grupo:
                grupo = "LTS"

            ano_alvo = None
            if opcao == "2":
                ano_alvo = input(f"[?] Qual ano limite para o grupo '{grupo}'? (ex: 2026)\n> ").strip()

            tarefas.append({"grupo": grupo, "ano": ano_alvo})
            print(f"\n[+] Grupo '{grupo}' adicionado à lista" + (f" (limite: {ano_alvo})" if ano_alvo else " (sem limite de ano)"))

            # Mostra resumo atual
            print("\n--- Lista de tarefas atual ---")
            for i, t in enumerate(tarefas, 1):
                limite = f"até {t['ano']}" if t['ano'] else "todas as páginas"
                print(f"  {i}. {t['grupo']} -> {limite}")

            adicionar = input("\n[?] Deseja adicionar mais um grupo? (S/N)\n> ").strip().upper()
            if adicionar != "S":
                break

        return opcao, tarefas

    def processar_grupo(self, grupo, ano_alvo, check_stop=None):
        """Processa um único grupo: seleciona, pagina e baixa os PDFs."""
        self.view.show_message(f"[GRUPO] Alterando para o grupo '{grupo}'...")
        self.model.select_group(grupo)
        self.model.set_download_subdir(grupo)

        safe_name = grupo.lower().strip()
        
        # Encontra a última página baixada
        import glob
        import re
        pdfs = glob.glob(os.path.join(self.model.download_dir, f"pagina * {safe_name}.pdf"))
        max_page = 0
        for pdf in pdfs:
            match = re.search(r'pagina (\d+)', os.path.basename(pdf))
            if match:
                num = int(match.group(1))
                if num > max_page:
                    max_page = num

        page = 1
        buscando_ano = False
        direcao = 1 # 1 para frente, -1 para trás

        if max_page > 1:
            self.view.show_message(f"   -> Última página baixada detectada: {max_page}. Pulando direto para ela...")
            if self.model.go_to_page(max_page):
                page = max_page
            else:
                self.view.show_message("   -> Falha ao pular. Retomando da página 1.")

        while True:
            if check_stop and check_stop():
                self.view.show_message(f"[!] Execução interrompida no grupo '{grupo}', página {page}.")
                break
                
            self.view.show_message(f"[PÁGINA {page}] Processando página {page} do grupo '{grupo}'...")

            # Verifica o ano ANTES de baixar
            if ano_alvo:
                ano_alvo_int = int(ano_alvo)
                anos_pagina = self.model.get_years_on_page()
                if anos_pagina:
                    min_ano = min(anos_pagina)
                    max_ano = max(anos_pagina)
                    
                    if min_ano > ano_alvo_int:
                        self.view.show_message(f"   -> Página contém apenas anos recentes ({min_ano}-{max_ano}). Pulando para frente...")
                        page += 1
                        direcao = 1
                        if not self.model.go_to_page(page):
                            self.view.show_message(f"   -> Não há mais páginas. Fim da lista.")
                            break
                        continue
                    elif max_ano < ano_alvo_int:
                        self.view.show_message(f"   -> Processos anteriores a {ano_alvo} encontrados ({max_ano}).")
                        
                        if direcao == -1 or buscando_ano:
                            # Se já estamos indo para trás ou buscando, significa que já vimos as páginas à frente
                            self.view.show_message(f"   -> Fim dos processos de {ano_alvo} alcançado (indo para trás).")
                            break
                        elif page > 1:
                            self.view.show_message(f"   -> Passamos do ano alvo. Voltando para procurar o ano {ano_alvo}...")
                            direcao = -1
                            buscando_ano = True
                            page -= 1
                            if self.model.go_to_page(page):
                                continue
                            break
                        else:
                            self.view.show_message("   -> Fim da busca por este ano.")
                            break

            # Se chegou aqui, a página contém o ano desejado ou não há filtro
            file_name = f"pagina {page} {safe_name}.pdf"
            file_path = os.path.join(self.model.download_dir, file_name)
            if os.path.exists(file_path):
                self.view.show_message(f"   -> Arquivo '{file_name}' já existe. Pulando download...")
            else:
                self.view.show_message(f"   -> Selecionando todos os itens da página {page}...")
                self.model.select_all_items()
                self.view.show_progress(page)
                self.model.click_download_button(page, grupo)

            if direcao == -1:
                self.view.show_message(f"   -> (Busca reversa) Retrocedendo para a página anterior...")
                page -= 1
                if page < 1:
                    self.view.show_message(f"   -> Chegou na primeira página. Busca reversa finalizada.")
                    break
            else:
                self.view.show_message(f"   -> Avançando para a próxima página...")
                page += 1
                
            if not self.model.go_to_page(page):
                self.view.show_message(f"   -> Não há mais páginas para o grupo '{grupo}'. Fim da lista.")
                break

        self.view.show_success(f"Download do grupo '{grupo}' finalizado! ({page} páginas processadas)")

    def run(self):
        try:
            # PASSO 0: Coleta todas as informações ANTES de abrir o navegador
            opcao, tarefas = self.coletar_tarefas()

            # Se escolheu apenas analisar PDFs
            if opcao == "analise":
                from models.pdf_analyzer import PdfAnalyzer
                self.view.show_message("Iniciando análise dos PDFs...")
                analyzer = PdfAnalyzer()
                success, msg = analyzer.analyze_pdfs_to_csv()
                if success:
                    self.view.show_success(msg)
                else:
                    self.view.show_error(msg)
                return

            # Pergunta se quer gerar CSV automaticamente no final
            fazer_analise = input("\n[?] Após o término dos downloads, deseja gerar os CSVs automaticamente? (S/N)\n> ").strip().upper()

            print("\n" + "="*60)
            self.view.show_message("Iniciando o navegador...")

            # URL de login do SEI Recife
            initial_url = "https://sip.recife.pe.gov.br/sip/login.php?sigla_orgao_sistema=PR&sigla_sistema=SEI&infra_url=L3NlaS8="

            self.model.open_initial_page(initial_url)

            # PASSO 1: Login automático
            self.view.show_message("[PASSO 1] Iniciando login automático...")
            self.model.auto_login("", "", "")
            self.view.show_success("[SUCESSO] Login concluído e possíveis modais fechados!")

            # PASSO 2: Navega para Acompanhamento Especial
            self.view.show_message("[PASSO 2] Navegando para a página Acompanhamento Especial...")
            self.model.navigate_to_acompanhamento()
            time.sleep(2)

            # PASSO 3: Processa cada grupo da lista de tarefas
            for i, tarefa in enumerate(tarefas, 1):
                print("\n" + "="*60)
                self.view.show_message(f"[TAREFA {i}/{len(tarefas)}] Iniciando grupo '{tarefa['grupo']}'...")
                print("="*60)
                self.processar_grupo(tarefa["grupo"], tarefa["ano"])

            print("\n" + "="*60)
            self.view.show_success("Todos os grupos foram processados com sucesso!")

            # Executa a análise automaticamente se o usuário escolheu 'S'
            if fazer_analise == 'S':
                from models.pdf_analyzer import PdfAnalyzer
                self.view.show_message("Iniciando análise automática dos PDFs...")
                analyzer = PdfAnalyzer()
                success, msg = analyzer.analyze_pdfs_to_csv()
                if success:
                    self.view.show_success(msg)
                else:
                    self.view.show_error(msg)

        except Exception as e:
            self.view.show_error(str(e))
        finally:
            input("\nPressione Enter no console para fechar o navegador e encerrar o script...")
            self.model.close()

    def run_gui(self, username, password, orgao, opcao, tarefas, fazer_analise, check_stop=None):
        """Executa o bot através dos dados fornecidos pela GUI."""
        try:
            # Se escolheu apenas analisar PDFs
            if opcao == "analise" or fazer_analise == 'S':
                pass # A análise será feita mais abaixo no final do método para todos os fluxos
                
            if opcao == "analise":
                from models.pdf_analyzer import PdfAnalyzer
                self.view.show_message("Iniciando análise dos PDFs...")
                analyzer = PdfAnalyzer()
                grupos_alvo = [t["grupo"] for t in tarefas] if tarefas else None
                success, msg = analyzer.analyze_pdfs_to_csv(grupos_alvo=grupos_alvo)
                if success:
                    self.view.show_success(msg)
                else:
                    self.view.show_error(msg)
                return

            self.view.show_message("Iniciando o navegador...")
            initial_url = "https://sip.recife.pe.gov.br/sip/login.php?sigla_orgao_sistema=PR&sigla_sistema=SEI&infra_url=L3NlaS8="

            self.model.open_initial_page(initial_url)

            # PASSO 1: Login automático
            self.view.show_message("[PASSO 1] Iniciando login automático...")
            self.model.auto_login(username, password, orgao)
            self.view.show_success("[SUCESSO] Login concluído e possíveis modais fechados!")

            # PASSO 2: Navega para Acompanhamento Especial
            self.view.show_message("[PASSO 2] Navegando para a página Acompanhamento Especial...")
            self.model.navigate_to_acompanhamento()
            time.sleep(2)

            # PASSO 3: Processa cada grupo da lista de tarefas
            for i, tarefa in enumerate(tarefas, 1):
                if check_stop and check_stop():
                    self.view.show_message("[!] Execução geral cancelada pelo usuário.")
                    break
                self.view.show_message(f"[TAREFA {i}/{len(tarefas)}] Iniciando grupo '{tarefa['grupo']}'...")
                self.processar_grupo(tarefa["grupo"], tarefa["ano"], check_stop=check_stop)

            if check_stop and check_stop():
                self.view.show_message("Processamento finalizado com cancelamento prévio.")
            else:
                self.view.show_success("Todos os grupos foram processados com sucesso!")

            # Executa a análise automaticamente
            if fazer_analise == 'S' or opcao == 'analise':
                from models.pdf_analyzer import PdfAnalyzer
                self.view.show_message("Iniciando análise automática dos PDFs para extração e quantitativos...")
                analyzer = PdfAnalyzer()
                grupos_alvo = [t["grupo"] for t in tarefas] if tarefas else None
                success, msg = analyzer.analyze_pdfs_to_csv(grupos_alvo=grupos_alvo)
                if success:
                    self.view.show_success(msg)
                else:
                    self.view.show_error(msg)

        except Exception as e:
            self.view.show_error(str(e))
        finally:
            self.view.show_message("Fechando navegador...")
            self.model.close()
