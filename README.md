# Validador de cargas Paytrack

Aplicativo Python local para transformar a planilha preenchida pelo cliente nos quatro modelos DEFAULT fornecidos. Não envia arquivos, não cria contas de e-mail e não importa dados no Paytrack.

## Uso

1. Abra `ValidadorPaytrack.exe` (versão Windows) ou execute `python app.py`.
2. Selecione a planilha do cliente. Os quatro modelos já acompanham o aplicativo.
3. Clique em **Analisar planilha**.
4. O programa pergunta se deseja revisar as decisões agora. Escolher Não mantém as pendências.
5. Em **Pendências**, selecione uma linha e clique em **Revisar seleção**. É possível selecionar várias linhas do mesmo campo para aplicar uma decisão em conjunto.
6. Em **Dados de saída**, edite qualquer campo de destino. Os originais permanecem intactos.
7. Para e-mails repetidos, defina a unidade do usuário e confirme seu domínio na aba **Domínios das unidades**. Em **Sugestões de e-mail**, revise individualmente ou clique em **Aplicar todas as sugestões**. A prévia mostra a lista completa e quantas alterações podem ser aplicadas. Clique em **Confirmar alterações** para aplicar o lote. Quando a unidade ainda não estiver definida, marque **Confirmo o uso dos domínios exibidos nas sugestões deste lote** para habilitar a aplicação dos endereços apresentados. A unidade continua pendente. Cancelar não altera os dados.
8. Use **Salvar revisão** para continuar depois. Ao reabrir, analise a mesma origem e clique em **Abrir revisão**.
9. **Exportar cargas** cria uma pasta nova com quatro `.xlsx`, `REVISAO.xlsx`, `revisao.json` e `LEIA-ME.txt`. Se houver pendências, o aplicativo pergunta se deseja exportar um rascunho.

## Regras implementadas

- **Resumo por aba:** mostra registros, ocorrências de erro, sugestões de e-mail, pendências e avisos para cada carga. Clique em uma quantidade para abrir a lista correspondente. As contagens são atualizadas após as decisões; erros e sugestões podem se referir aos mesmos registros e não devem ser somados.

- Cabeçalhos, ordem de colunas e nomes das abas dos modelos preservados.
- Uma linha da origem corresponde a uma linha de saída. Duplicados não são removidos.
- CNPJ/CPF/CEP e códigos são tratados como texto, preservando zeros existentes. Não se inventam zeros perdidos.
- `SIM`/`NÃO` são normalizados para `S`/`N`; `BRASIL` para `BRA`.
- Datas válidas são gravadas como datas Excel. Datas inválidas permanecem pendentes para revisão.
- Campos obrigatórios, opções de cabeçalho, formato de CPF e e-mail e duplicidades são verificados.
- Havendo dois códigos de integração, nenhum é escolhido automaticamente. Havendo apenas um, ele é copiado; a unidade continua dependente da informação da origem ou da decisão do usuário.
- E-mails repetidos são comparados sem diferenças entre maiúsculas/minúsculas e espaços externos.
- Sugestão: primeiro nome + último sobrenome sem acentos + domínio confirmado da unidade. Havendo colisão, um sufixo numérico é proposto, sem aplicação automática.
- Enquanto o domínio da unidade não estiver confirmado, a sugestão baseada no e-mail original é apenas provisória e não pode ser aceita pelo botão de sugestões.
- Campos sem equivalente no destino, incluindo políticas de despesas, são preservados no relatório de origem.
- Fórmulas em campos de origem não são executadas. Relatórios gravam textos como valores literais.
- A sessão é vinculada ao conteúdo da origem e dos modelos; decisões de outro arquivo são recusadas.
- Senhas são ocultadas na interface e no relatório. Alterações de senha não são persistidas no arquivo de revisão.

## Limites desta versão

Esta versão usa os layouts fornecidos nesta tarefa. Modelos com cabeçalhos diferentes são recusados para evitar conversões incorretas. O cadastro externo de ERP/Paytrack não é consultado. As decisões 2 a 7 adiadas na conversa não foram transformadas em regras de negócio adicionais: não há validação de alçadas, existência de contas contábeis ou políticas corporativas. Não valida situação cadastral nem dígitos verificadores de CPF/CNPJ. A conclusão local não comprova que o importador do Paytrack aceitará a carga.

O campo `Identificador Pai (*)` não existe na origem. Nenhuma hierarquia é inferida: sua semântica e preenchimento precisam ser definidos pelo usuário. Despesas não recebem códigos inventados nem quantificação automática. A aba de instruções da origem é documentação, não carga.

Os arquivos contêm dados pessoais. O aplicativo funciona localmente e a versão distribuída não inclui a base EXTRAFRUTI. Os relatórios e sessões que você salvar contêm dados da revisão.

## Executar pelo Python

Python 3.12 ou superior, com Tkinter instalado:

```powershell
python -m pip install -r requirements.txt
python app.py
```

## Gerar o executável no Windows

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --name ValidadorPaytrack --add-data "templates;templates" --add-data "schema.json;." app.py
```

O executável é gerado em `dist`. Os modelos vazios são incorporados. A base do cliente é selecionada depois, na interface.

## Testes

```powershell
python -m unittest discover -s tests -v
```

Os testes usam dados fictícios temporários e verificam decisões, colisões, persistência, preservação dos modelos e exportação.
