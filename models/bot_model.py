import time
import os
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
        chrome_options = Options()
        
        # Pasta raiz de downloads
        self.download_root = os.path.join(os.getcwd(), "downloads")
        if not os.path.exists(self.download_root):
            os.makedirs(self.download_root)
        
        # Subpasta atual (será definida para cada grupo)
        self.download_dir = self.download_root
            
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

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

    def click_download_button(self, page_number, grupo_name=""):
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
            
            # Salva a página como PDF usando recursos do Selenium 4
            from selenium.webdriver.common.print_page_options import PrintOptions
            print_options = PrintOptions()
            pdf_base64 = self.driver.print_page(print_options)
            
            # Nome do arquivo: "pagina 1 lts.pdf"
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

    def get_years_on_page(self):
        anos = set()
        try:
            print("[LOG-MODELO] Escaneando datas da tabela em busca de anos presentes...")
            tds = self.driver.find_elements(By.XPATH, "//table[@id='tblAcompanhamento']//td | //td[contains(@class, 'tdAcompanhamento')]")
            for td in tds:
                texto = td.text.strip()
                if len(texto) >= 10 and texto[2] == '/' and texto[5] == '/':
                    ano_tabela_str = texto[6:10]
                    if ano_tabela_str.isdigit():
                        anos.add(int(ano_tabela_str))
        except Exception as e:
            print(f"[LOG-MODELO] Erro ao ler datas da tabela: {e}")
        return anos
            
    def close(self):
        self.driver.quit()
