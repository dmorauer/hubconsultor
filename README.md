# Validador de Cargas Paytrack (Next.js Web Application)

Aplicação web desenvolvida em Next.js para validação, revisão e exportação das cargas de importação e sincronizador do Paytrack.

## Funcionalidades

- **Processamento 100% no Navegador:** As planilhas são lidas e convertidas via JavaScript/TypeScript no cliente sem envio para servidores externos.
- **Validação de Cargas e Modelos:** Suporte aos modelos DEFAULT (Empresas, Centros de Custo, Tipos de Despesa, Colaboradores).
- **Hierarquia do Sincronizador:** Suporte e validação de árvores de hierarquia com visualização e exportação de CSVs.
- **Correções em Lote e Sugestões:** Correção de formatos, e-mails e códigos de integração.
- **Exportação:** Geração de pacotes ZIP com arquivos `.xlsx` e `.csv`.

## Como Executar

### Requisitos

- Node.js 18+

### Desenvolvimento

```bash
cd web
npm install
npm run dev
```

Acesse [http://localhost:3000](http://localhost:3000).

### Build para Produção

```bash
cd web
npm run build
npm run start
```
