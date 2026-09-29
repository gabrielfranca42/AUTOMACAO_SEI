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

        pdf_files = [f for f in os.listdir(self.download_dir) if f.endswith('.pdf')]
        if not pdf_files:
            return False, "Nenhum arquivo PDF encontrado na pasta downloads."

        extracted_data = []
        
        # Regex básico para tentar extrair os dados. 
        # Como o formato pode variar, uma abordagem por partes é melhor.
        
        for file in pdf_files:
            file_path = os.path.join(self.download_dir, file)
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
                                'Arquivo Origem': file,
                                'Processo': processo,
                                'Usuário': usuario,
                                'Data': data,
                                'Hora': hora,
                                'Grupo': grupo,
                                'Observação': observacao
                            })
                            
            except Exception as e:
                print(f"Erro ao processar {file}: {e}")

        if not extracted_data:
            return False, "Nenhum dado válido foi extraído dos PDFs."

        df = pd.DataFrame(extracted_data)
        
        # Adiciona colunas de Mês e Ano baseadas na Data para facilitar o agrupamento
        # A data esperada está no formato DD/MM/YYYY
        df['Mês'] = df['Data'].str[3:5]
        df['Ano'] = df['Data'].str[6:10]
        
        # Salva os dados detalhados no CSV
        output_path = os.path.join(os.getcwd(), output_filename)
        df.to_csv(output_path, index=False, sep=';', encoding='utf-8-sig')
        
        # Gera o quantitativo (resumo) agrupado por Ano, Mês e Grupo
        if not df.empty and 'Mês' in df.columns and 'Ano' in df.columns:
            resumo_df = df.groupby(['Ano', 'Mês', 'Grupo']).size().reset_index(name='Quantidade')
            resumo_df = resumo_df.sort_values(by=['Ano', 'Mês', 'Grupo'], ascending=[False, False, True])
            
            resumo_path = os.path.join(os.getcwd(), "resumo_quantitativo.csv")
            
            # Escreve o cabeçalho personalizado
            with open(resumo_path, 'w', encoding='utf-8-sig') as f:
                f.write(f"Quantitativo Geral:;{len(df)}\n")
                f.write("\nQuantitativo por Mês e Grupo:\n")
            
            # Adiciona os dados do dataframe em seguida
            resumo_df.to_csv(resumo_path, mode='a', index=False, sep=';', encoding='utf-8-sig')
            
            msg_resumo = f"\nResumo quantitativo salvo em resumo_quantitativo.csv"
        else:
            msg_resumo = ""
        
        return True, f"Extração concluída com sucesso! {len(extracted_data)} registros salvos em {output_filename}.{msg_resumo}"
