## 2026-07-27

### Concluido
- GUI refatorada: interface em abas (Gerenciar Contas / Login)
- Login por checkboxes com relogging automatico (monitora janela via IsWindow)
- Auto-login: contas com flag auto_login iniciam automaticamente ao abrir o bot
- Adicionado campo auto_login no cadastro de conta (AccountDialog)
- Limpeza: removidos window_utils.py, vision.py, input_utils.py
- Removidos PNGs orfaos e debug PNGs da raiz
- Documentacao atualizada: copilot-instructions, PROJECT_MAP, BACKLOG, MIGRATION_PROGRESS
- Migracao do config: Settings em src/config/settings.py como fonte unica
  - config.py raiz convertido em shim de compatibilidade
  - Container passa templates_dir absoluto para VisionService
  - main_window.py nao depende mais de config.py

### Proxima etapa
- Implementar logger estruturado
- Implementar testes

## 2026-07-21

### Commit 0018

- Criado VisionService
- Integrado ao GameClient
- LoginWorkflow nao depende mais de vision.py

Status:
🟢 Funcionando

## 2026-07-20

### Concluido
- Estrutura da aplicacao finalizada.
- ServiceContainer implementado.
- Application implementado.
- AutomationEngine implementado.

### Proxima etapa
- Migrar conexao com a janela para o LoginWorkflow.
