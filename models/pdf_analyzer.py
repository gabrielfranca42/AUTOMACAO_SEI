import os
import re
import pandas as pd
import PyPDF2

class PdfAnalyzer:
    def __init__(self):
        self.download_dir = os.path.join(os.getcwd(), "downloads")

    def analyze_pdfs_to_csv(self, output_filename="dados_extraidos.csv"):
        if not os.path.exists(self.download_dir):
            return False, f"A pasta {self.download_dir} não existe."

        pdf_files = []
        for root, dirs, files in os.walk(self.download_dir):
            for file in files:
                if file.endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))

        if not pdf_files:
            return False, "Nenhum arquivo PDF encontrado na pasta downloads ou em suas subpastas."

        extracted_data = []
        
        # Regex básico para tentar extrair os dados. 
        # Como o formato pode variar, uma abordagem por partes é melhor.
        
        for file_path in pdf_files:
            try:
                reader = PyPDF2.PdfReader(file_path)
                for page in reader.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    # Dividir o texto usando o padrão de início de processo "32."
                    chunks = text.split("32.")
                    for chunk in chunks[1:]: # Ignora o cabeçalho antes do primeiro "32."
                        chunk = "32." + chunk
                        
                        # Extração básica baseada em expressões regulares
                        # Exemplo de linha: 32.001058/2026-41 livia.morais 08/01/2026\n12:56:44LTS ALEXANDRA  DA SILVA\nMEDEIROS 1064207
                        
                        # Tentando pegar o número do processo (que pode ter espaços indevidos)
                        processo_match = re.search(r'(32\.\d{3}\s?\d{3}/\d{4}-\d{2})', chunk)
                        processo = processo_match.group(1).replace(" ", "") if processo_match else ""
                        
                        # Usuário e Data
                        user_date_match = re.search(r'([a-z\.]+)\s+(\d{2}/\d{2}/\d{4})', chunk)
                        usuario = user_date_match.group(1) if user_date_match else ""
                        data = user_date_match.group(2) if user_date_match else ""
                        
                        # Hora e Grupo
                        time_group_match = re.search(r'(\d{2}:\d{2}:\d{2})([A-Z]+)', chunk)
                        hora = time_group_match.group(1) if time_group_match else ""
                        grupo = time_group_match.group(2) if time_group_match else ""
                        
                        # Observação (o resto do texto após a hora/grupo)
                        if time_group_match:
                            pos_start = time_group_match.end()
                            observacao_bruta = chunk[pos_start:].strip()
                            # Remove espaços múltiplos e quebras de linha
                            observacao = re.sub(r'\s+', ' ', observacao_bruta)
                            # Pega até encontrar espaços duplos no final do chunk (indicativo do fim do registro no extrator pypdf) ou fim do texto
                            observacao = observacao.split("  ")[0].strip()
                        else:
                            observacao = ""
                        
                        if processo:
                            extracted_data.append({
                                'Arquivo Origem': os.path.basename(file_path),
                                'Processo': processo,
                                'Usuário': usuario,
                                'Data': data,
                                'Hora': hora,
                                'Grupo': grupo,
                                'Observação': observacao
                            })
                            
            except Exception as e:
                print(f"Erro ao processar {file_path}: {e}")

        if not extracted_data:
            return False, "Nenhum dado válido foi extraído dos PDFs."

        df = pd.DataFrame(extracted_data)
        
        # Adiciona colunas de Mês e Ano baseadas na Data para facilitar o agrupamento
        # A data esperada está no formato DD/MM/YYYY
        df['Mês'] = df['Data'].str[3:5]
        df['Ano'] = df['Data'].str[6:10]
        
        # Salva os dados detalhados no CSV
        output_path = os.path.join(os.getcwd(), output_filename)
        aviso_erro = ""
        try:
            df.to_csv(output_path, index=False, sep=';', encoding='utf-8-sig')
        except PermissionError:
            aviso_erro += f"\n[!] AVISO: Não foi possível atualizar o '{output_filename}' pois ele está aberto em outro programa (ex: Excel)."
        except Exception as e:
            aviso_erro += f"\n[!] Erro ao salvar '{output_filename}': {e}"
        
        # Gera o quantitativo (resumo) agrupado por Ano, Mês e Grupo
        if not df.empty and 'Mês' in df.columns and 'Ano' in df.columns:
            resumo_df = df.groupby(['Ano', 'Mês', 'Grupo']).size().reset_index(name='Quantidade')
            resumo_df = resumo_df.sort_values(by=['Ano', 'Mês', 'Grupo'], ascending=[False, False, True])
            
            resumo_path = os.path.join(os.getcwd(), "resumo_quantitativo.csv")
            
            try:
                # Escreve o cabeçalho personalizado
                with open(resumo_path, 'w', encoding='utf-8-sig') as f:
                    f.write(f"Quantitativo Geral:;{len(df)}\n")
                    f.write("\nQuantitativo por Mês e Grupo:\n")
                
                # Adiciona os dados do dataframe em seguida
                resumo_df.to_csv(resumo_path, mode='a', index=False, sep=';', encoding='utf-8-sig')
            except PermissionError:
                aviso_erro += f"\n[!] AVISO: Não foi possível atualizar o 'resumo_quantitativo.csv' pois está aberto."
            except Exception as e:
                aviso_erro += f"\n[!] Erro ao salvar resumo: {e}"
            
            # Prepara a string de resumo para ser exibida na interface (independente de ter salvo o CSV ou não)
            texto_resumo = f"\nQUANTITATIVO MENSAL:\n------------------------\nTotal Geral: {len(df)} processos\n"
            for index, row in resumo_df.iterrows():
                texto_resumo += f"[{row['Mês']}/{row['Ano']}] {row['Grupo']}: {row['Quantidade']} processo(s)\n"
            
            msg_resumo = f"\nResumo gerado com sucesso.{aviso_erro}\n{texto_resumo}"
        else:
            msg_resumo = f"\nNão foi possível gerar quantitativos.{aviso_erro}"
        
        return True, f"Extração concluída! {len(extracted_data)} registros lidos.{msg_resumo}"
