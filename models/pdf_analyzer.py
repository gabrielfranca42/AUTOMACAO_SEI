import os
import re
import pandas as pd
import PyPDF2

class PdfAnalyzer:
    def __init__(self):
        self.download_dir = os.path.join(os.getcwd(), "downloads")
        
        # Lista de grupos conhecidos para extração precisa
        self.known_groups = [
            "ABONO PERMANENCIA", "ANOTAÇÃO", "APOSENTADORIA POR INVALIDEZ", "APOSENTADORIA", 
            "AULA ATIVIDADE", "AUXÍLIO FUNERAL", "AVERBAÇÃO", "CARGA HORÁRIA", "CASAMENTO", "CAT", 
            "CERTIDÃO/DECLARAÇÃO", "CREDENCIAMENTO", "CTC", "DECLARAÇÃO DE VÍNCULO", "DEPENDENTE", 
            "DESAVERBAÇÃO", "DESLIGAMENTOS", "DIFÍCIL ACESSO", "ENQUADRAMENTO ADI", 
            "FICHA FINANCEIRA / FICHA FUNCIONAL", "GOZO DE FÉRIAS", "HORA EXTRA", "HORARIO ESPECIAL", 
            "INSALUBRIDADE", "ISENÇÃO DE IMPOSTO DE RENDA", "LDPF", "LICENÇA LUTO", 
            "LICENÇA MATERNIDADE POR ADOÇÃO", "LICENÇA MATERNIDADE", 
            "LICENÇA PARA CASAMENTO", "LICENÇA PARA TRATO DE INTERRESSE PARTICULAR", 
            "LICENÇA PATERNIDADE", "LICENÇA PRÊMIO", "LTS", "MUDANÇA DE NIVEL", "PROGRESSÃO/TITULAÇÃO", 
            "READAPTAÇÃO", "RECONSIDERAÇÃO DE ACRESCIMO", "RECONSIDERAÇÃO DE DESPACHO", "REDUÇÃO DE ATIVIDADES", 
            "REINTEGRAÇÃO", "REQUERIMENTO", "RESTOS DEIXADOS", "REVISÃO DE VENCIMENTOS", "SALÁRIO FAMÍLIA", 
            "VALE ALIMENTAÇÃO"
        ]
        # Ordenar por tamanho decrescente para priorizar nomes mais longos (ex: "LICENÇA MATERNIDADE POR ADOÇÃO" antes de "LICENÇA MATERNIDADE")
        self.known_groups.sort(key=len, reverse=True)

    def _extrair_dados_de_pdfs(self, grupos_alvo=None):
        """Extrai todos os dados dos PDFs encontrados na pasta downloads.
        Retorna lista de dicts com os dados extraídos de cada registro."""
        if not os.path.exists(self.download_dir):
            return [], f"A pasta {self.download_dir} não existe."

        pdf_files = []
        for root, dirs, files in os.walk(self.download_dir):
            for file in files:
                if file.endswith('.pdf'):
                    if grupos_alvo:
                        grupos_alvo_upper = [g.upper() for g in grupos_alvo]
                        rel_path = os.path.relpath(root, self.download_dir).upper()
                        if not any(g in rel_path for g in grupos_alvo_upper):
                            continue
                    pdf_files.append(os.path.join(root, file))

        if not pdf_files:
            return [], "Nenhum arquivo PDF encontrado na pasta downloads."

        extracted_data = []
        for file_path in pdf_files:
            # Identifica o tipo de processo pela pasta do arquivo
            rel_path = os.path.relpath(file_path, self.download_dir)
            pasta_processo = rel_path.split(os.sep)[0] if os.sep in rel_path else ""
            
            try:
                reader = PyPDF2.PdfReader(file_path)
                for page in reader.pages:
                    text = page.extract_text()
                    if not text: continue
                    
                    # Regex resiliente para achar o número do processo (mesmo com espaços em qualquer parte)
                    # Ex: 32.0391 15/2026-64 ou 32.039275/2026-1 1
                    matches = list(re.finditer(r'32\.\s*\d[\d\s]*/\d{4}-\s*\d[\d\s]*\d', text))
                    
                    for i in range(len(matches)):
                        start_pos = matches[i].start()
                        end_pos = matches[i+1].start() if i+1 < len(matches) else len(text)
                        chunk = text[start_pos:end_pos]
                        
                        # Processo limpo sem espaços
                        processo = matches[i].group(0).replace(" ", "")
                        
                        user_date_match = re.search(r'([a-z\._]+)\s+(\d{2}/\d{2}/\d{4})', chunk)
                        usuario = user_date_match.group(1) if user_date_match else ""
                        data = user_date_match.group(2) if user_date_match else ""
                        
                        time_match = re.search(r'(\d{2}:\d{2}:\d{2})', chunk)
                        hora = time_match.group(1) if time_match else ""
                        
                        grupo = ""
                        observacao = ""
                        
                        if time_match:
                            rest_after_time = chunk[time_match.end():].strip()
                            
                            # Encontrar o grupo exato baseado na lista conhecida
                            # Ignora quebras de linha que possam ter partido o nome do grupo no PDF
                            rest_clean = rest_after_time.replace('\n', ' ')
                            matched_group = False
                            for g in self.known_groups:
                                if rest_clean.startswith(g):
                                    grupo = g
                                    observacao = rest_clean[len(g):].strip()
                                    matched_group = True
                                    break
                            
                            if not matched_group:
                                # Se não achou na lista conhecida, extrai a primeira palavra colada ou próxima
                                fallback_match = re.match(r'([A-ZÇÃÕÁÉÍÓÚ]+(?:[\s/][A-ZÇÃÕÁÉÍÓÚ]+)*)', rest_clean)
                                if fallback_match:
                                    grupo = fallback_match.group(1).strip()
                                    observacao = rest_clean[len(grupo):].strip()
                            
                            # Limpar espaços extras na observação
                            observacao = re.sub(r'\s+', ' ', observacao)
                        
                        if processo:
                            extracted_data.append({
                                'Tipo Processo': pasta_processo,
                                'Arquivo Origem': os.path.basename(file_path),
                                'Processo': processo, 'Usuário': usuario,
                                'Data': data, 'Hora': hora, 'Grupo': grupo, 'Observação': observacao
                            })
            except Exception as e: 
                print(f"Erro no PDF {file_path}: {e}")

        return extracted_data, None

    def _gerar_csv_geral(self, df, output_dir):
        """Gera o CSV geral (resumo_quantitativo.csv) com:
        - Total geral de toda a busca
        - Quantitativo por Ano
        - Quantitativo por Ano e Tipo de Processo
        - Divisão detalhada por tipo de processo com mês/ano e quantitativo"""
        resumo_path = os.path.join(output_dir, "resumo_quantitativo.csv")
        
        total_geral = len(df)
        tipos = sorted(df['Tipo Processo'].unique())
        anos = sorted(df['Ano'].dropna().unique(), reverse=True)
        
        linhas = []
        linhas.append("RESUMO GERAL DE PROCESSOS")
        linhas.append(f"Total Geral de Registros:;{total_geral}")
        linhas.append(f"Tipos de Processo Encontrados:;{len(tipos)}")
        linhas.append("")
        linhas.append("=" * 60)
        
        # ============================================
        # SEÇÃO 1: Quantitativo por Ano (totais gerais)
        # ============================================
        linhas.append("")
        linhas.append("QUANTITATIVO POR ANO")
        linhas.append("Ano;Quantidade")
        resumo_ano = df.groupby('Ano').size().reset_index(name='Quantidade')
        resumo_ano = resumo_ano.sort_values(by='Ano', ascending=False)
        for _, row in resumo_ano.iterrows():
            linhas.append(f"{row['Ano']};{row['Quantidade']}")
        
        linhas.append("")
        linhas.append("=" * 60)
        
        # ============================================
        # SEÇÃO 2: Quantitativo por Ano e Tipo de Processo
        # ============================================
        linhas.append("")
        linhas.append("QUANTITATIVO POR ANO E TIPO DE PROCESSO")
        linhas.append("")
        
        for ano in anos:
            df_ano = df[df['Ano'] == ano]
            total_ano = len(df_ano)
            linhas.append(f"ANO {ano};Total:;{total_ano}")
            linhas.append("Tipo de Processo;Quantidade")
            
            resumo_tipo_ano = df_ano.groupby('Tipo Processo').size().reset_index(name='Quantidade')
            resumo_tipo_ano = resumo_tipo_ano.sort_values(by='Quantidade', ascending=False)
            
            for _, row in resumo_tipo_ano.iterrows():
                linhas.append(f"{row['Tipo Processo']};{row['Quantidade']}")
            
            linhas.append("")
            linhas.append("-" * 40)
            linhas.append("")
        
        linhas.append("=" * 60)
        
        # ============================================
        # SEÇÃO 3: Detalhamento por Tipo de Processo (mês/ano)
        # ============================================
        linhas.append("")
        linhas.append("DETALHAMENTO POR TIPO DE PROCESSO")
        linhas.append("")
        
        for tipo in tipos:
            df_tipo = df[df['Tipo Processo'] == tipo]
            total_tipo = len(df_tipo)
            
            linhas.append(f"TIPO DE PROCESSO:;{tipo}")
            linhas.append(f"Total:;{total_tipo}")
            linhas.append("")
            linhas.append("Ano;Mês;Quantidade")
            
            # Agrupa por Ano e Mês
            if 'Ano' in df_tipo.columns and 'Mês' in df_tipo.columns:
                resumo_mes = df_tipo.groupby(['Ano', 'Mês']).size().reset_index(name='Quantidade')
                resumo_mes = resumo_mes.sort_values(by=['Ano', 'Mês'], ascending=[False, False])
                
                for _, row in resumo_mes.iterrows():
                    linhas.append(f"{row['Ano']};{row['Mês']};{row['Quantidade']}")
            
            linhas.append("")
            linhas.append("-" * 40)
            linhas.append("")
        
        # Escreve o arquivo
        with open(resumo_path, 'w', encoding='utf-8-sig') as f:
            f.write("\n".join(linhas))
        
        return resumo_path

    def _gerar_csvs_por_processo(self, df, output_dir):
        """Gera um CSV individual para cada tipo de processo na pasta 'csv_por_processo'.
        Cada CSV contém: nome do processo, quantitativo e todos os dados extraídos."""
        csv_dir = os.path.join(output_dir, "csv_por_processo")
        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir)
        
        tipos = sorted(df['Tipo Processo'].unique())
        arquivos_gerados = []
        
        for tipo in tipos:
            df_tipo = df[df['Tipo Processo'] == tipo].copy()
            total_tipo = len(df_tipo)
            
            # Nome do arquivo sanitizado
            safe_name = tipo.strip().replace("/", "-").replace("\\", "-")
            if not safe_name:
                safe_name = "SEM_TIPO"
            csv_path = os.path.join(csv_dir, f"{safe_name}.csv")
            
            # Escreve o cabeçalho com nome e quantitativo
            with open(csv_path, 'w', encoding='utf-8-sig') as f:
                f.write(f"Tipo de Processo:;{tipo}\n")
                f.write(f"Total de Registros:;{total_tipo}\n")
                f.write("\n")
            
            # Colunas de dados (exclui 'Tipo Processo' pois já está no cabeçalho)
            colunas_dados = [c for c in df_tipo.columns if c != 'Tipo Processo']
            df_export = df_tipo[colunas_dados]
            
            # Adiciona os dados completos
            df_export.to_csv(csv_path, mode='a', index=False, sep=';', encoding='utf-8-sig')
            
            arquivos_gerados.append(csv_path)
        
        return arquivos_gerados

    def analyze_pdfs_to_csv(self, grupos_alvo=None):
        """Método principal: extrai dados dos PDFs e gera todos os CSVs.
        Retorna (sucesso: bool, mensagem: str)"""
        
        # 1. Extrai dados dos PDFs
        extracted_data, erro = self._extrair_dados_de_pdfs(grupos_alvo)
        
        if erro:
            return False, erro
        
        if not extracted_data:
            return False, "Nenhum dado extraído dos PDFs."
        
        # 2. Cria DataFrame e adiciona colunas de Mês e Ano
        df = pd.DataFrame(extracted_data)
        df['Mês'] = df['Data'].str[3:5]
        df['Ano'] = df['Data'].str[6:10]
        
        output_dir = os.getcwd()
        aviso_erro = ""
        
        # 3. Gera CSV com todos os dados brutos (dados_extraidos.csv)
        try:
            dados_path = os.path.join(output_dir, "dados_extraidos.csv")
            df.to_csv(dados_path, index=False, sep=';', encoding='utf-8-sig')
        except Exception as e:
            aviso_erro += f"\n[!] Erro ao salvar dados_extraidos.csv: {e}"
        
        # 4. Gera CSV geral com resumo por tipo de processo (resumo_quantitativo.csv)
        try:
            resumo_path = self._gerar_csv_geral(df, output_dir)
        except Exception as e:
            aviso_erro += f"\n[!] Erro ao salvar resumo_quantitativo.csv: {e}"
        
        # 5. Gera CSVs individuais por tipo de processo
        try:
            arquivos_processo = self._gerar_csvs_por_processo(df, output_dir)
        except Exception as e:
            aviso_erro += f"\n[!] Erro ao gerar CSVs por processo: {e}"
            arquivos_processo = []
        
        # 6. Monta mensagem de resumo para o log
        total_geral = len(df)
        tipos = sorted(df['Tipo Processo'].unique())
        
        texto_resumo = f"\nQUANTITATIVOS:\n{'='*40}\n"
        texto_resumo += f"Total Geral: {total_geral} processos\n"
        texto_resumo += f"Tipos de Processo: {len(tipos)}\n"
        texto_resumo += f"CSVs individuais gerados: {len(arquivos_processo)}\n"
        texto_resumo += f"\nPor Tipo de Processo:\n{'-'*30}\n"
        
        for tipo in tipos:
            df_tipo = df[df['Tipo Processo'] == tipo]
            texto_resumo += f"\n  {tipo}: {len(df_tipo)} processo(s)\n"
            
            # Mostra resumo por mês/ano
            if 'Ano' in df_tipo.columns and 'Mês' in df_tipo.columns:
                resumo_mes = df_tipo.groupby(['Ano', 'Mês']).size().reset_index(name='Quantidade')
                resumo_mes = resumo_mes.sort_values(by=['Ano', 'Mês'], ascending=[False, False])
                for _, row in resumo_mes.iterrows():
                    texto_resumo += f"    [{row['Mês']}/{row['Ano']}]: {row['Quantidade']} processo(s)\n"
        
        msg = f"\nExtração concluída! {len(extracted_data)} registros lidos."
        msg += f"\n\nArquivos gerados:"
        msg += f"\n  - dados_extraidos.csv (todos os dados brutos)"
        msg += f"\n  - resumo_quantitativo.csv (resumo geral por tipo)"
        msg += f"\n  - csv_por_processo/ ({len(arquivos_processo)} arquivos individuais)"
        msg += f"{aviso_erro}\n{texto_resumo}"
        
        return True, msg
