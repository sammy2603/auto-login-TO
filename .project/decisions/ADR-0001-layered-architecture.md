# ADR-0001

## O produto será desenvolvido utilizando Arquitetura em Camadas.

### Motivo

Separar regras de negócio da implementação técnica.

### Consequências

As funcionalidades não dependerão diretamente de bibliotecas como OpenCV ou PyWin32.

Toda comunicação ocorrerá através de serviços especializados.

Isso permitirá substituir implementações no futuro sem alterar as regras de negócio.