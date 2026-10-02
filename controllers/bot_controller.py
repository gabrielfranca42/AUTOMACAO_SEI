import time
import os
import re
from models.bot_model import SeiBotModel
from views.console_view import ConsoleView


class BotController:
    def __init__(self, view=None):
        self.model = SeiBotModel()
        self.view = view if view else ConsoleView()

    @staticmethod
    def _date_to_sortable(date_str):
        parts = date_str.split('/')
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            return f"{parts[2]}{parts[1]}{parts[0]}"
        return "00000000"

    def _build_filename(self, page, safe_name, page_info):
        month = page_info.get('month') or '00'
        year = page_info.get('year') or '0000'
        first_date = page_info.get('first_date')
        first_time = page_info.get('first_time')
        date_formatted = first_date.replace('/', '-') if first_date else '00-00-0000'
        time_formatted = first_time[:5].replace(':', 'h') if first_time else '00h00'
        return f"pagina {page} {safe_name} {month}-{year} {date_formatted}_{time_formatted}.pdf"

    def _find_max_page(self, download_dir):
        max_page = 0
        if not os.path.exists(download_dir): return 0
        for f in os.listdir(download_dir):
            if f.endswith('.pdf'):
                match = re.search(r'pagina (\d+)', f)
                if match: max_page = max(max_page, int(match.group(1)))
        return max_page

    def _file_exists_for_page(self, download_dir, page, safe_name):
        try:
            prefix = f"pagina {page} "
            for f in os.listdir(download_dir):
                if f.endswith('.pdf') and f.startswith(prefix):
                    return True, f
        except Exception: pass
        return False, None

    def _verificar_filtros(self, page_info, page, ano_alvo, mes_alvo, data_alvo, direcao, buscando_alvo):
        all_dates = page_info.get('all_dates', [])
        all_years = page_info.get('all_years', set())
        if not all_dates and not all_years: return 'processar'

        sortable_dates = [self._date_to_sortable(d) for d in all_dates]
        sortable_dates = [d for d in sortable_dates if d != "00000000"]

        if data_alvo:
            target = self._date_to_sortable(data_alvo)
            if sortable_dates:
                if min(sortable_dates) > target: return 'avançar'
                elif max(sortable_dates) < target:
                    if direcao == -1 or buscando_alvo: return 'parar'
                    elif page > 1: return 'recuar'
                    else: return 'parar'
            return 'processar'

        if mes_alvo:
            parts = mes_alvo.split('/')
            if len(parts) == 2:
                target_start, target_end = f"{parts[1]}{parts[0]}01", f"{parts[1]}{parts[0]}31"
                if sortable_dates:
                    if min(sortable_dates) > target_end: return 'avançar'
                    elif max(sortable_dates) < target_start:
                        if direcao == -1 or buscando_alvo: return 'parar'
                        elif page > 1: return 'recuar'
                        else: return 'parar'
            return 'processar'

        if ano_alvo:
            ano_alvo_int = int(ano_alvo)
            if all_years:
                if min(all_years) > ano_alvo_int: return 'avançar'
                elif max(all_years) < ano_alvo_int:
                    if direcao == -1 or buscando_alvo: return 'parar'
                    elif page > 1: return 'recuar'
                    else: return 'parar'

        return 'processar'

    def coletar_tarefas(self):
        tarefas = []
        opcao = input("\n[1] Baixar [2] Extrair CSV [3] Ambos\n> ").strip()
        if opcao == "2":
            grupo = input("Qual grupo analisar? (Vazio=todos)\n> ").strip().upper()
            if grupo: tarefas.append({"grupo": grupo, "ano": None, "mes": None, "data": None})
            return "analise", tarefas
        
        while True:
            grupo = input("GRUPO (Ex: LTS)\n> ").strip().upper() or "LTS"
            filtro = input("Filtro: [1] Ano [2] Mês [3] Data [4] Sem filtro\n> ").strip()
            a, m, d = None, None, None
            if filtro == "1": a = input("Ano?\n> ").strip()
            elif filtro == "2": m = input("Mês/Ano?\n> ").strip()
            elif filtro == "3": d = input("Data?\n> ").strip()
            tarefas.append({"grupo": grupo, "ano": a, "mes": m, "data": d})
            if input("Mais um? (S/N)\n> ").strip().upper() != "S": break
        return opcao, tarefas

    def processar_grupo(self, grupo, ano_alvo=None, mes_alvo=None, data_alvo=None, check_stop=None):
        try:
            self.view.show_message(f"Alterando para o grupo '{grupo}'...")
            self.model.select_group(grupo)
        except Exception as e:
            self.view.show_error(f"Erro grupo '{grupo}': {e}. Pulando...")
            return

        self.model.set_download_subdir(grupo)
        safe_name = grupo.lower().strip()
        max_page = self._find_max_page(self.model.download_dir)
        page = max_page if max_page > 1 and self.model.go_to_page(max_page) else 1
        buscando_alvo, direcao = False, 1

        while True:
            if check_stop and check_stop(): break
            page_info = self.model.get_page_info()
            if ano_alvo or mes_alvo or data_alvo:
                res = self._verificar_filtros(page_info, page, ano_alvo, mes_alvo, data_alvo, direcao, buscando_alvo)
                if res == 'avançar':
                    page += 1; direcao = 1
                    if not self.model.go_to_page(page): break
                    continue
                elif res == 'recuar':
                    direcao = -1; buscando_alvo = True; page -= 1
                    if page < 1 or not self.model.go_to_page(page): break
                    continue
                elif res == 'parar': break

            file_name = self._build_filename(page, safe_name, page_info)
            exists, existing_name = self._file_exists_for_page(self.model.download_dir, page, safe_name)

            if exists:
                if existing_name != file_name and page_info.get('first_date'):
                    try:
                        os.rename(os.path.join(self.model.download_dir, existing_name), 
                                  os.path.join(self.model.download_dir, file_name))
                        self.view.show_message(f"Renomeado: '{existing_name}' -> '{file_name}'")
                    except Exception as e: pass
            else:
                self.model.select_all_items()
                self.model.click_download_button(page, grupo, custom_filename=file_name)

            if direcao == -1:
                page -= 1
                if page < 1: break
            else: page += 1
            if not self.model.go_to_page(page): break

    def renomear_pdfs_antigos(self, grupos_alvo=None):
        import PyPDF2
        d_root = os.path.join(os.getcwd(), "downloads")
        if not os.path.exists(d_root): return
        gnorm = [g.upper().strip().replace("/", "-").replace("\\", "-") for g in grupos_alvo] if grupos_alvo else None

        for g_dir in sorted(os.listdir(d_root)):
            g_path = os.path.join(d_root, g_dir)
            if not os.path.isdir(g_path) or (gnorm and g_dir.upper() not in gnorm): continue
            for pdf_file in sorted(os.listdir(g_path)):
                if not pdf_file.endswith('.pdf') or re.search(r'\d{2}-\d{4}', pdf_file): continue
                match = re.match(r'pagina (\d+) (.+)\.pdf$', pdf_file)
                if not match: continue
                pdf_path = os.path.join(g_path, pdf_file)
                try:
                    reader = PyPDF2.PdfReader(pdf_path)
                    first_date, first_time = None, None
                    for pg in reader.pages:
                        text = pg.extract_text()
                        if not text: continue
                        dm = re.search(r'(\d{2}/\d{2}/\d{4})', text)
                        if dm:
                            first_date = dm.group(1)
                            tm = re.search(r'(\d{2}:\d{2}:\d{2})', text)
                            if tm: first_time = tm.group(1)
                            break
                    if first_date:
                        date_formatted = first_date.replace('/', '-')
                        time_formatted = first_time[:5].replace(':', 'h') if first_time else "00h00"
                        new_name = f"pagina {match.group(1)} {match.group(2)} {first_date[3:5]}-{first_date[6:10]} {date_formatted}_{time_formatted}.pdf"
                        if not os.path.exists(os.path.join(g_path, new_name)):
                            os.rename(pdf_path, os.path.join(g_path, new_name))
                except: pass

    def run(self):
        # Implementation for terminal, skipped for brevity in this rewrite as GUI is main entry point
        pass

    def run_gui(self, username, password, orgao, opcao, tarefas, fazer_analise, renomear_pdfs=False, check_stop=None):
        grupos_alvo = [t["grupo"] for t in tarefas] if tarefas else None
        try:
            # Modo: SÓ EXTRAIR CSV
            if opcao == "analise":
                self.renomear_pdfs_antigos(grupos_alvo)
                self._executar_extracao_csv(grupos_alvo)
                return
            
            # Modo: SÓ RENOMEAR
            if opcao == "renomear":
                self.renomear_pdfs_antigos(grupos_alvo)
                self.view.show_message("Renomeação concluída!")
                return

            # Modo: DOWNLOAD (com opcionais de renomear e CSV)
            self.model.open_initial_page("https://sip.recife.pe.gov.br/sip/login.php?sigla_orgao_sistema=PR&sigla_sistema=SEI&infra_url=L3NlaS8=")
            self.model.auto_login(username, password, orgao)
            self.model.navigate_to_acompanhamento()
            time.sleep(2)

            for tarefa in tarefas:
                if check_stop and check_stop(): break
                self.processar_grupo(tarefa["grupo"], tarefa.get("ano"), tarefa.get("mes"), tarefa.get("data"), check_stop)
            
            self.view.show_message("Downloads concluídos!")
            
        except Exception as e:
            self.view.show_error(str(e))
        finally:
            self.model.close()
        
        # Após finalizar downloads (e fechar o browser), gera renomeação e CSV se solicitado
        try:
            if renomear_pdfs:
                self.view.show_message("Renomeando PDFs...")
                self.renomear_pdfs_antigos(grupos_alvo)
            
            if fazer_analise == 'S':
                self._executar_extracao_csv(grupos_alvo)
        except Exception as e:
            self.view.show_error(f"Erro pós-download: {e}")

    def _executar_extracao_csv(self, grupos_alvo=None):
        """Executa a extração de dados dos PDFs e geração de CSVs, mostrando resultado no log."""
        self.view.show_message("Iniciando extração de dados dos PDFs e geração de CSVs...")
        from models.pdf_analyzer import PdfAnalyzer
        analyzer = PdfAnalyzer()
        sucesso, mensagem = analyzer.analyze_pdfs_to_csv(grupos_alvo)
        if sucesso:
            self.view.show_success(mensagem)
        else:
            self.view.show_error(mensagem)
