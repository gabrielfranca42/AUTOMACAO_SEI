import time
import os
import re
import base64
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

class SeiBotModel:
    def __init__(self):
        # Pasta raiz de downloads
        self.download_root = os.path.join(os.getcwd(), "downloads")
        if not os.path.exists(self.download_root):
            os.makedirs(self.download_root)
        
        # Subpasta atual (será definida para cada grupo)
        self.download_dir = self.download_root
        
        # Browser com inicialização sob demanda (lazy init)
        self._driver = None
        self._wait = None

    def _ensure_browser(self):
        """Inicializa o navegador somente quando necessário."""
        if self._driver is None:
            chrome_options = Options()
            self._driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), 
                options=chrome_options
            )
            self._wait = WebDriverWait(self._driver, 10)

    @property
    def driver(self):
        self._ensure_browser()
        return self._driver
    
    @property
    def wait(self):
        self._ensure_browser()
        return self._wait

    def set_download_subdir(self, grupo_name):
        """Cria e define a subpasta de downloads para o grupo atual."""
        # Sanitiza o nome do grupo para usar como nome de pasta
        safe_name = grupo_name.strip().replace("/", "-").replace("\\", "-")
        self.download_dir = os.path.join(self.download_root, safe_name)
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        print(f"[LOG-MODELO] Pasta de download definida: {self.download_dir}")

    def open_initial_page(self, url):
        self.driver.get(url)

    def auto_login(self, username, password, orgao):
        print("[LOG-MODELO] Aguardando campo de usuário aparecer...")
        user_input = self.wait.until(EC.presence_of_element_located((By.ID, "txtUsuario")))
        user_input.send_keys(username)
        
        print("[LOG-MODELO] Preenchendo senha e selecionando órgão...")
        pass_input = self.driver.find_element(By.ID, "pwdSenha")
        pass_input.send_keys(password)
        
        orgao_select = self.driver.find_element(By.ID, "selOrgao")
        select = Select(orgao_select)
        select.select_by_visible_text(orgao)
        
        print("[LOG-MODELO] Clicando no botão de Acessar...")
        submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit'] | //button[@id='sbmLogin'] | //button[contains(text(), 'Acessar')]")
        submit_btn.click()
        
        print("[LOG-MODELO] Aguardando carregamento da tela inicial do SEI após login...")
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//span[text()='Acompanhamento Especial'] | //div[@id='divInfraBarraNavegacao'] | //div[@id='divInfraAreaTela']")))
        
        # Tenta fechar o aviso da Escola de Governo ou outros popups
        self.fechar_popups_iniciais()

    def fechar_popups_iniciais(self):
        try:
            print("[LOG-MODELO] Verificando se há avisos/popups na tela...")
            # Pressiona ESCAPE para tentar fechar o modal
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
            
            # Tenta clicar em botões comuns de fechar modal
            botoes_fechar = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'close')] | //div[contains(@id, 'Modal')]//button | //button[@title='Fechar'] | //img[@title='Fechar']/..")
            for btn in botoes_fechar:
                if btn.is_displayed():
                    print("[LOG-MODELO] Clicando no botão fechar [X] do popup...")
                    btn.click()
                    time.sleep(1)
        except Exception as e:
            print(f"[LOG-MODELO] Tratamento de popups: {e}")

    def navigate_to_acompanhamento(self):
        print("[LOG-MODELO] Buscando menu lateral de Acompanhamento Especial...")
        menu_link = self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[@link='acompanhamento_listar'] | //span[text()='Acompanhamento Especial']/parent::a")))
        print("[LOG-MODELO] Clicando no menu de Acompanhamento Especial...")
        try:
            menu_link.click()
        except:
            print("[LOG-MODELO] Clique normal bloqueado (talvez por um popup). Forçando clique via JavaScript...")
            self.driver.execute_script("arguments[0].click();", menu_link)
            
    def select_group(self, group_text):
        # Encontra o select pelo ID mostrado na imagem
        select_element = self.wait.until(
            EC.presence_of_element_located((By.ID, "selGrupoAcompanhamento"))
        )
        select = Select(select_element)
        select.select_by_visible_text(group_text)
        time.sleep(2) # Aguarda a página recarregar após a mudança

    def select_all_items(self):
        try:
            # Baseado na sua imagem, o SEI usa uma imagem como checkbox com o ID 'imgInfraCheck'
            print("[LOG-MODELO] Buscando o botão de selecionar todos (imgInfraCheck)...")
            checkbox_all = self.wait.until(
                EC.presence_of_element_located((By.ID, "imgInfraCheck"))
            )
            
            title = checkbox_all.get_attribute("title") or ""
            
            # Se a palavra 'Remover' não estiver no title, significa que não está selecionado ainda
            if "Remover" not in title:
                print("[LOG-MODELO] Marcando todos os itens da tabela...")
                self.driver.execute_script("arguments[0].click();", checkbox_all)
                time.sleep(1)
            else:
                print("[LOG-MODELO] Os itens já estavam todos selecionados.")
                
            return True
        except Exception as e:
            print(f"[LOG-MODELO] Erro ao selecionar itens: {e}")
            return False

    def get_page_info(self):
        """Extrai informações detalhadas de data/hora da tabela da página atual.
        Retorna dict com: first_date, first_time, month, year, all_dates, all_years"""
        info = {
            'first_date': None,
            'first_time': None,
            'month': None,
            'year': None,
            'all_dates': [],
            'all_years': set()
        }
        try:
            print("[LOG-MODELO] Extraindo informações de data/hora da página...")
            tds = self.driver.find_elements(By.XPATH, 
                "//table[@id='tblAcompanhamento']//td | //td[contains(@class, 'tdAcompanhamento')]")
            
            for td in tds:
                texto = td.text.strip()
                # Procura padrão de data DD/MM/YYYY
                date_matches = re.findall(r'(\d{2}/\d{2}/\d{4})', texto)
                for date_str in date_matches:
                    info['all_dates'].append(date_str)
                    ano_str = date_str[6:10]
                    if ano_str.isdigit():
                        info['all_years'].add(int(ano_str))
                    
                    # Captura o primeiro registro encontrado
                    if info['first_date'] is None:
                        info['first_date'] = date_str
                        info['month'] = date_str[3:5]
                        info['year'] = date_str[6:10]
                        
                        # Tenta encontrar horário no mesmo texto
                        time_match = re.search(r'(\d{2}:\d{2}:\d{2})', texto)
                        if time_match:
                            info['first_time'] = time_match.group(1)
        except Exception as e:
            print(f"[LOG-MODELO] Erro ao extrair info da página: {e}")
        
        return info

    def get_years_on_page(self):
        """Método de compatibilidade. Retorna set de anos encontrados na página."""
        info = self.get_page_info()
        return info['all_years']

    def click_download_button(self, page_number, grupo_name="", custom_filename=None):
        """Baixa a página atual como PDF.
        Se custom_filename for fornecido, usa-o. Caso contrário, gera nome padrão."""
        main_window = None
        try:
            # Desativa o dialog de impressão do navegador para não travar o bot
            self.driver.execute_script("window.print = function() {};")
            
            # Clica no botão pelo ID fornecido na imagem
            btn_imprimir = self.wait.until(EC.element_to_be_clickable((By.ID, "btnImprimir")))
            
            main_window = self.driver.current_window_handle
            btn_imprimir.click()
            time.sleep(2) # Aguarda a ação
            
            # O SEI geralmente abre uma nova janela/popup para a versão de impressão
            if len(self.driver.window_handles) > 1:
                for window in self.driver.window_handles:
                    if window != main_window:
                        self.driver.switch_to.window(window)
                        break
            
            # Garante que a tabela não fique cortada na hora do print (força via CSS universal focado na impressão)
            self.driver.execute_script("""
                var css = `
                    @media print {
                        html, body, form, fieldset, div, table, tbody, tr, td {
                            height: auto !important;
                            max-height: none !important;
                            overflow: visible !important;
                            position: relative !important;
                            display: block !important;
                        }
                        table { display: table !important; }
                        tbody { display: table-row-group !important; }
                        tr { display: table-row !important; page-break-inside: avoid !important; }
                        td, th { display: table-cell !important; }
                        #divInfraAreaTela, #divInfraAreaTabela, .infraAreaTela, .infraAreaTabela {
                            position: relative !important;
                            height: auto !important;
                            overflow: visible !important;
                        }
                    }
                `;
                var style = document.createElement('style');
                style.innerHTML = css;
                document.head.appendChild(style);
                
                var iframes = document.querySelectorAll('iframe');
                for(var i=0; i<iframes.length; i++){
                    try {
                        var iframeStyle = iframes[i].contentWindow.document.createElement('style');
                        iframeStyle.innerHTML = css;
                        iframes[i].contentWindow.document.head.appendChild(iframeStyle);
                    } catch(e) {}
                }
            """)
            time.sleep(1) # Aguarda o layout se ajustar

            # Salva a página como PDF usando recursos do Selenium 4
            from selenium.webdriver.common.print_page_options import PrintOptions
            print_options = PrintOptions()
            # Define uma página extremamente longa (60 cm) para evitar que a tabela seja cortada na quebra de página
            print_options.page_height = 60.0
            print_options.page_width = 21.0
            
            pdf_base64 = self.driver.print_page(print_options)
            
            # Nome do arquivo
            if custom_filename:
                file_name = custom_filename
            else:
                grupo_label = grupo_name.lower().strip() if grupo_name else "grupo"
                file_name = f"pagina {page_number} {grupo_label}.pdf"
            
            file_path = os.path.join(self.download_dir, file_name)
            
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(pdf_base64))
            
            print(f"[LOG-MODELO] PDF salvo: {file_path}")
                
            # Fecha a popup de impressão e volta pra principal
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(main_window)
                
            return True
        except Exception as e:
            print(f"Erro ao salvar PDF da página {page_number}: {e}")
            # Tenta voltar para a janela principal em caso de erro
            try:
                if main_window and len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(main_window)
            except:
                pass
            return False

    def go_to_page(self, page_number):
        try:
            select_element = self.driver.find_element(By.ID, "selInfraPaginacaoInferior")
            from selenium.webdriver.support.ui import Select
            select = Select(select_element)
            
            # Options typically have the text '1', '2', etc.
            # We can select by visible text
            select.select_by_visible_text(str(page_number))
            time.sleep(2) # Aguarda recarregar
            return True
        except Exception as e:
            print(f"Erro ao pular para a página {page_number}: {e}")
            return False

    def go_to_next_page(self):
        try:
            # Encontra o select de paginação mostrado na imagem
            select_element = self.driver.find_element(By.ID, "selInfraPaginacaoInferior")
            from selenium.webdriver.support.ui import Select
            select = Select(select_element)
            
            # Pega todas as opções (páginas disponíveis) e a selecionada atualmente
            options = select.options
            current_index = -1
            
            # Encontra o índice da página atual
            for i, option in enumerate(options):
                if option.is_selected():
                    current_index = i
                    break
                    
            # Verifica se há uma próxima página (se não estamos na última opção)
            if current_index != -1 and current_index + 1 < len(options):
                # Seleciona a próxima página pelo índice
                select.select_by_index(current_index + 1)
                time.sleep(2) # Aguarda a tabela recarregar
                return True
            else:
                # Chegou na última página
                return False
        except Exception as e:
            print(f"Erro ao mudar de página ou não há paginação: {e}")
            return False
            
    def close(self):
        if self._driver:
            self._driver.quit()
            self._driver = None
            self._wait = None
