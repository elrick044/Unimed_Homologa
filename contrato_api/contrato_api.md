# Contrato da API

## Base URL

```text
/api
```

## Autenticacao

A API utiliza JWT via Simple JWT.

Endpoints publicos atuais:

- `POST /api/auth/register/prestador/`
- `POST /api/auth/login/`

Endpoints autenticados devem enviar o token de acesso no header:

```http
Authorization: Bearer <access_token>
```

Endpoints autenticados atuais:

- `GET /api/prestador/processo/`
- `GET /api/documentos/tipos/`
- `POST /api/documentos/upload/`
- `GET /api/admin/processos/`
- `GET /api/processos/<id_processo>/documentos/`
- `POST /api/admin/documentos/<id_documento>/validar/`

## POST /api/auth/register/prestador/

Cadastra um prestador de servico e cria o usuario de acesso vinculado ao e-mail informado.

### Request

```json
{
  "razao_social": "Clinica Exemplo LTDA",
  "nome_fantasia": "Clinica Exemplo",
  "cnpj": "12.345.678/0001-90",
  "endereco": "Rua Central, 100",
  "nome_responsavel": "Maria Silva",
  "email": "prestador@example.com",
  "telefone": "(11) 99999-9999",
  "senha": "SenhaForte123"
}
```

### Campos

| Campo | Tipo | Obrigatorio | Regra |
| --- | --- | --- | --- |
| `razao_social` | string | Sim | Maximo 255 caracteres |
| `nome_fantasia` | string | Sim | Maximo 255 caracteres |
| `cnpj` | string | Sim | Formato `00.000.000/0000-00` ou 14 digitos; deve ser unico |
| `endereco` | string | Sim | Texto livre |
| `nome_responsavel` | string | Sim | Maximo 255 caracteres |
| `email` | string | Sim | E-mail valido; deve ser unico para login |
| `telefone` | string | Sim | Maximo 20 caracteres |
| `senha` | string | Sim | Minimo 8 caracteres e validada pelas regras de senha do Django |

### Response 201

```json
{
  "id": 1,
  "razao_social": "Clinica Exemplo LTDA",
  "nome_fantasia": "Clinica Exemplo",
  "cnpj": "12345678000190",
  "endereco": "Rua Central, 100",
  "nome_responsavel": "Maria Silva",
  "email": "prestador@example.com",
  "telefone": "(11) 99999-9999",
  "criado_em": "2026-05-06T20:30:00Z",
  "atualizado_em": "2026-05-06T20:30:00Z"
}
```

Observacoes:

- A senha nunca e retornada pela API.
- A senha e armazenada com hash pelo mecanismo nativo do Django.
- O CNPJ e salvo normalizado, apenas com digitos.
- O usuario criado recebe o perfil `PRESTADOR`.
- Um `ProcessoHomologacao` e criado automaticamente com status `CADASTRO_INICIADO`.
- O historico do processo recebe o evento `Cadastro criado`.

### Response 400

Erros de validacao retornam os campos com mensagens.

Exemplo de CNPJ invalido:

```json
{
  "cnpj": [
    "CNPJ deve estar no formato 00.000.000/0000-00 ou conter 14 digitos."
  ]
}
```

Exemplo de e-mail ja cadastrado:

```json
{
  "email": [
    "Ja existe um usuario cadastrado com este e-mail."
  ]
}
```

## POST /api/auth/login/

Autentica um usuario por e-mail e senha e retorna um par de tokens JWT.

### Request

```json
{
  "email": "prestador@example.com",
  "senha": "SenhaForte123"
}
```

### Campos

| Campo | Tipo | Obrigatorio | Regra |
| --- | --- | --- | --- |
| `email` | string | Sim | E-mail cadastrado |
| `senha` | string | Sim | Senha do usuario |

### Response 200

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

### Response 400

Credenciais invalidas ou usuario inativo retornam erro de validacao.

Exemplo:

```json
{
  "non_field_errors": [
    "E-mail ou senha invalidos."
  ]
}
```

## POST /api/documentos/upload/

Recebe um ou mais documentos PDF do prestador autenticado e salva os arquivos no storage padrao do Django, em `media/documentos/`.

Requer autenticacao JWT de usuario com perfil `PRESTADOR`.

### Headers

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

### Request com um documento

Campos multipart:

| Campo | Tipo | Obrigatorio | Regra |
| --- | --- | --- | --- |
| `arquivo` | file | Sim | Arquivo PDF com `Content-Type: application/pdf`, extensao `.pdf` e assinatura `%PDF` |
| `tipo_documento` | integer | Sim | ID de um `TipoDocumento` ativo |

Exemplo conceitual:

```text
arquivo=<contrato.pdf>
tipo_documento=1
```

### Request com multiplos documentos

Campos multipart repetidos:

| Campo | Tipo | Obrigatorio | Regra |
| --- | --- | --- | --- |
| `arquivos` | file[] | Sim | Um ou mais arquivos PDF com `Content-Type: application/pdf`, extensao `.pdf` e assinatura `%PDF` |
| `tipos_documento` | integer[] | Sim | Um tipo para cada arquivo, na mesma ordem |

Exemplo conceitual:

```text
arquivos=<contrato.pdf>
tipos_documento=1
arquivos=<comprovante-endereco.pdf>
tipos_documento=2
```

### Response 201

```json
{
  "documentos": [
    {
      "id": 10,
      "tipo_documento": {
        "id": 1,
        "nome": "Contrato Social",
        "descricao": "",
        "obrigatorio": true,
        "ativo": true,
        "criado_em": "2026-05-07T20:30:00Z",
        "atualizado_em": "2026-05-07T20:30:00Z"
      },
      "arquivo": "/media/documentos/contrato.pdf",
      "content_type": "application/pdf",
      "tamanho_bytes": 123456,
      "status": "ENVIADO",
      "versao": 1,
      "documento_anterior": null,
      "validado_por_email": null,
      "validado_em": null,
      "motivo_reprovacao": null,
      "observacoes": null,
      "enviado_em": "2026-05-07T20:35:00Z"
    }
  ]
}
```

### Response 400

Arquivo ausente:

```json
{
  "arquivos": [
    "Envie ao menos um arquivo PDF."
  ]
}
```

Arquivo que nao seja PDF:

```json
{
  "arquivos": [
    "O arquivo contrato.txt deve ser um PDF."
  ]
}
```

Quantidade de arquivos diferente da quantidade de tipos:

```json
{
  "tipos_documento": [
    "Informe um tipo de documento para cada arquivo enviado."
  ]
}
```

Tipo de documento invalido ou inativo:

```json
{
  "tipos_documento": [
    "Tipo de documento invalido ou inativo."
  ]
}
```

### Response 401

Retornado quando o token JWT esta ausente, invalido ou expirado.

### Response 403

Retornado quando o usuario autenticado nao possui perfil `PRESTADOR` ou nao possui cadastro de prestador vinculado.

Exemplo:

```json
{
  "detail": "Apenas prestadores podem enviar documentos."
}
```

### Observabilidade

O backend registra logs estruturados para:

- `document_upload_success`
- `document_upload_invalid_format`
- `document_upload_size_anomaly`
- `document_upload_validation_failed`
- `document_upload_forbidden_profile`
- `document_upload_missing_prestador`

Observacoes:

- Cada documento enviado fica vinculado ao `ProcessoHomologacao` vigente do prestador.
- Cada documento salvo gera um evento `Documento enviado` no historico do processo.
- Quando um novo arquivo e enviado para um `TipoDocumento` que ja possui documento ativo no mesmo processo:
  - o documento anterior recebe status `SUBSTITUIDO`;
  - o novo documento recebe `versao = versao_anterior + 1`;
  - o novo documento referencia o anterior em `documento_anterior`;
  - o historico recebe o evento `Documento substituido`.
- Apos o upload, o backend recalcula o status do processo:
  - `DOCUMENTACAO_PENDENTE` quando ainda existem documentos obrigatorios pendentes.
  - `EM_VALIDACAO` quando todos os documentos obrigatorios ativos foram enviados.

## GET /api/prestador/processo/

Retorna o resumo completo da jornada do prestador autenticado: status atual, pendencias, documentos enviados e historico de eventos.

Requer autenticacao JWT de usuario com perfil `PRESTADOR`.

### Headers

```http
Authorization: Bearer <access_token>
```

### Response 200

```json
{
  "id": 1,
  "prestador": {
    "id": 1,
    "razao_social": "Clinica Exemplo LTDA",
    "nome_fantasia": "Clinica Exemplo",
    "cnpj": "12345678000190",
    "endereco": "Rua Central, 100",
    "nome_responsavel": "Maria Silva",
    "email": "prestador@example.com",
    "telefone": "(11) 99999-9999",
    "criado_em": "2026-05-10T10:00:00Z",
    "atualizado_em": "2026-05-10T10:00:00Z"
  },
  "status_atual": "DOCUMENTACAO_PENDENTE",
  "criado_em": "2026-05-10T10:00:00Z",
  "atualizado_em": "2026-05-10T10:20:00Z",
  "concluido_em": null,
  "pendencias": [
    {
      "id": 2,
      "nome": "Comprovante de Endereco",
      "descricao": "Comprovante atualizado do endereco informado.",
      "obrigatorio": true,
      "ativo": true,
      "criado_em": "2026-05-10T10:00:00Z",
      "atualizado_em": "2026-05-10T10:00:00Z"
    }
  ],
  "documentos_enviados": [
    {
      "id": 10,
      "tipo_documento": {
        "id": 1,
        "nome": "Contrato Social",
        "descricao": "Documento de constituicao da empresa.",
        "obrigatorio": true,
        "ativo": true,
        "criado_em": "2026-05-10T10:00:00Z",
        "atualizado_em": "2026-05-10T10:00:00Z"
      },
      "arquivo": "/media/documentos/contrato.pdf",
      "content_type": "application/pdf",
      "tamanho_bytes": 123456,
      "status": "ENVIADO",
      "versao": 1,
      "documento_anterior": null,
      "validado_por_email": null,
      "validado_em": null,
      "motivo_reprovacao": null,
      "observacoes": null,
      "enviado_em": "2026-05-10T10:20:00Z"
    }
  ],
  "historico": [
    {
      "id": 5,
      "acao": "Documento enviado",
      "descricao": "Documento Contrato Social enviado pelo prestador.",
      "usuario_email": "prestador@example.com",
      "metadados": {
        "documento_id": 10,
        "tipo_documento_id": 1,
        "arquivo_nome": "contrato.pdf",
        "tamanho_bytes": 123456
      },
      "criado_em": "2026-05-10T10:20:00Z"
    }
  ]
}
```

### Response 401

Retornado quando o token JWT esta ausente, invalido ou expirado.

## GET /api/processos/<id_processo>/documentos/

Lista os documentos de um processo agrupados por tipo de documento, incluindo o documento atual e o historico de versoes.

Perfis administrativos podem consultar qualquer processo. Prestadores podem consultar apenas o proprio processo.

### Headers

```http
Authorization: Bearer <access_token>
```

### Response 200

```json
{
  "processo": 1,
  "documentos": [
    {
      "tipo_documento": {
        "id": 1,
        "nome": "Contrato Social",
        "descricao": "Documento de constituicao da empresa.",
        "obrigatorio": true,
        "ativo": true,
        "criado_em": "2026-05-11T10:00:00Z",
        "atualizado_em": "2026-05-11T10:00:00Z"
      },
      "documento_atual": {
        "id": 12,
        "tipo_documento": {
          "id": 1,
          "nome": "Contrato Social",
          "descricao": "Documento de constituicao da empresa.",
          "obrigatorio": true,
          "ativo": true,
          "criado_em": "2026-05-11T10:00:00Z",
          "atualizado_em": "2026-05-11T10:00:00Z"
        },
        "arquivo": "/media/documentos/contrato-v2.pdf",
        "content_type": "application/pdf",
        "tamanho_bytes": 124000,
        "status": "ENVIADO",
        "versao": 2,
        "documento_anterior": 10,
        "validado_por_email": null,
        "validado_em": null,
        "motivo_reprovacao": null,
        "observacoes": null,
        "enviado_em": "2026-05-11T11:00:00Z"
      },
      "versoes": [
        {
          "id": 12,
          "status": "ENVIADO",
          "versao": 2,
          "documento_anterior": 10,
          "validado_por_email": null,
          "validado_em": null,
          "motivo_reprovacao": null,
          "observacoes": null,
          "enviado_em": "2026-05-11T11:00:00Z"
        },
        {
          "id": 10,
          "status": "SUBSTITUIDO",
          "versao": 1,
          "documento_anterior": null,
          "validado_por_email": "analista@example.com",
          "validado_em": "2026-05-11T10:30:00Z",
          "motivo_reprovacao": "Documento ilegivel.",
          "observacoes": "Enviar novamente com melhor qualidade.",
          "enviado_em": "2026-05-11T10:00:00Z"
        }
      ]
    }
  ]
}
```

### Response 401

Retornado quando o token JWT esta ausente, invalido ou expirado.

### Response 403

Retornado quando o usuario nao possui acesso ao processo informado.

## GET /api/admin/processos/

Lista todos os processos de homologacao para uso administrativo.

Apenas usuarios com perfil `EQUIPE_ADMINISTRATIVA` ou `ADMINISTRADOR` podem acessar.

### Headers

```http
Authorization: Bearer <access_token>
```

### Response 200

```json
{
  "processos": [
    {
      "id": 1,
      "prestador": {
        "id": 1,
        "razao_social": "Clinica Exemplo LTDA",
        "nome_fantasia": "Clinica Exemplo",
        "cnpj": "12345678000190",
        "endereco": "Rua Central, 100",
        "nome_responsavel": "Maria Silva",
        "email": "prestador@example.com",
        "telefone": "(11) 99999-9999",
        "criado_em": "2026-05-13T10:00:00Z",
        "atualizado_em": "2026-05-13T10:00:00Z"
      },
      "status_atual": "DOCUMENTACAO_PENDENTE",
      "total_documentos": 2,
      "total_pendencias": 1,
      "ultimo_evento": {
        "id": 7,
        "acao": "Documento enviado",
        "descricao": "Documento Contrato Social enviado pelo prestador.",
        "usuario_email": "prestador@example.com",
        "metadados": {
          "documento_id": 10,
          "tipo_documento_id": 1,
          "arquivo_nome": "contrato.pdf",
          "tamanho_bytes": 123456,
          "versao": 1,
          "documento_anterior_id": null
        },
        "criado_em": "2026-05-13T10:30:00Z"
      },
      "criado_em": "2026-05-13T10:00:00Z",
      "atualizado_em": "2026-05-13T10:30:00Z",
      "concluido_em": null
    }
  ]
}
```

### Response 401

Retornado quando o token JWT esta ausente, invalido ou expirado.

### Response 403

Retornado quando o usuario autenticado nao possui perfil administrativo.

## POST /api/admin/documentos/<id_documento>/validar/

Valida individualmente um documento enviado. Apenas usuarios com perfil `EQUIPE_ADMINISTRATIVA` ou `ADMINISTRADOR` podem acessar.

### Headers

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Request

```json
{
  "status": "REPROVADO",
  "motivo_reprovacao": "Documento ilegivel.",
  "observacoes": "Enviar novamente com melhor qualidade."
}
```

### Campos

| Campo | Tipo | Obrigatorio | Regra |
| --- | --- | --- | --- |
| `status` | string | Sim | Aceita apenas `APROVADO` ou `REPROVADO` |
| `motivo_reprovacao` | string | Condicional | Obrigatorio quando `status` for `REPROVADO` |
| `observacoes` | string | Nao | Observacoes internas da validacao |

### Response 200

```json
{
  "id": 10,
  "tipo_documento": {
    "id": 1,
    "nome": "Contrato Social",
    "descricao": "Documento de constituicao da empresa.",
    "obrigatorio": true,
    "ativo": true,
    "criado_em": "2026-05-11T10:00:00Z",
    "atualizado_em": "2026-05-11T10:00:00Z"
  },
  "arquivo": "/media/documentos/contrato.pdf",
  "content_type": "application/pdf",
  "tamanho_bytes": 123456,
  "status": "REPROVADO",
  "versao": 1,
  "documento_anterior": null,
  "validado_por_email": "analista@example.com",
  "validado_em": "2026-05-11T10:30:00Z",
  "motivo_reprovacao": "Documento ilegivel.",
  "observacoes": "Enviar novamente com melhor qualidade.",
  "enviado_em": "2026-05-11T10:00:00Z"
}
```

Observacoes:

- A validacao registra `validado_por` e `validado_em`.
- A validacao gera evento `Documento validado` no historico do processo.
- Quando o documento e reprovado, o processo passa para `CORRECAO_SOLICITADA`.
- Quando todos os documentos obrigatorios ativos estao aprovados, o processo passa para `EM_APROVACAO_INTERNA`.

### Response 400

Exemplo de reprovacao sem motivo:

```json
{
  "motivo_reprovacao": [
    "Informe o motivo da reprovacao."
  ]
}
```

### Response 401

Retornado quando o token JWT esta ausente, invalido ou expirado.

### Response 403

Retornado quando o usuario autenticado nao possui perfil administrativo.

### Response 403

Retornado quando o usuario autenticado nao possui perfil `PRESTADOR` ou nao possui cadastro de prestador vinculado.

Exemplo:

```json
{
  "detail": "Apenas prestadores podem consultar este processo."
}
```

## GET /api/documentos/tipos/

Lista os tipos de documentos ativos que podem ser usados no upload.

Requer autenticacao JWT.

### Headers

```http
Authorization: Bearer <access_token>
```

### Response 200

```json
{
  "tipos_documento": [
    {
      "id": 1,
      "nome": "Contrato Social",
      "descricao": "Documento de constituicao da empresa.",
      "obrigatorio": true,
      "ativo": true,
      "criado_em": "2026-05-07T20:30:00Z",
      "atualizado_em": "2026-05-07T20:30:00Z"
    },
    {
      "id": 2,
      "nome": "Comprovante de Endereco",
      "descricao": "Comprovante atualizado do endereco informado.",
      "obrigatorio": true,
      "ativo": true,
      "criado_em": "2026-05-07T20:30:00Z",
      "atualizado_em": "2026-05-07T20:30:00Z"
    }
  ]
}
```

### Tipos padrao

A migracao inicial de dados cria os seguintes tipos ativos:

- `Contrato Social`
- `Comprovante de Endereco`
- `Alvara de Funcionamento`
- `Certidao Negativa`

### Response 401

Retornado quando o token JWT esta ausente, invalido ou expirado.

## Modelos Base

### Usuario

| Campo | Descricao |
| --- | --- |
| `email` | Identificador unico usado para login |
| `perfil` | `PRESTADOR`, `EQUIPE_ADMINISTRATIVA` ou `ADMINISTRADOR` |
| `password` | Hash da senha gerenciado pelo Django |

### PrestadorEmpresa

| Campo | Descricao |
| --- | --- |
| `user` | Relacao 1:1 com o usuario |
| `razao_social` | Razao social da empresa |
| `nome_fantasia` | Nome fantasia da empresa |
| `cnpj` | CNPJ unico, salvo com 14 digitos |
| `endereco` | Endereco da empresa |
| `nome_responsavel` | Responsavel pelo cadastro |
| `email` | E-mail do prestador |
| `telefone` | Telefone de contato |
| `criado_em` | Data de criacao |
| `atualizado_em` | Data da ultima atualizacao |

### ProcessoHomologacao

| Campo | Descricao |
| --- | --- |
| `prestador` | Relacao 1:1 com o prestador |
| `status` | Status formal da jornada de homologacao |
| `criado_em` | Data de criacao do processo |
| `atualizado_em` | Data da ultima atualizacao |
| `concluido_em` | Data de conclusao, quando aplicavel |

Status permitidos:

- `CADASTRO_INICIADO`
- `DOCUMENTACAO_PENDENTE`
- `EM_VALIDACAO`
- `CORRECAO_SOLICITADA`
- `EM_APROVACAO_INTERNA`
- `REPROVADO`
- `APROVADO`
- `MINUTA_GERADA`
- `PROCESSO_CONCLUIDO`

### HistoricoProcesso

| Campo | Descricao |
| --- | --- |
| `processo` | Processo vinculado ao evento |
| `acao` | Nome curto do evento, como `Cadastro criado` ou `Documento enviado` |
| `descricao` | Detalhe textual opcional |
| `usuario` | Usuario responsavel pelo evento, quando houver |
| `metadados` | Dados estruturados do evento |
| `criado_em` | Data e hora do evento |

### TipoDocumento

| Campo | Descricao |
| --- | --- |
| `nome` | Nome configuravel do documento, como `Contrato Social` |
| `descricao` | Texto opcional de apoio |
| `obrigatorio` | Indica se o documento e obrigatorio para homologacao |
| `ativo` | Indica se o tipo pode ser usado em novos uploads |
| `criado_em` | Data de criacao |
| `atualizado_em` | Data da ultima atualizacao |

### DocumentoPrestador

| Campo | Descricao |
| --- | --- |
| `prestador` | Prestador vinculado ao documento |
| `processo` | Processo de homologacao vinculado ao documento |
| `tipo_documento` | Tipo de documento enviado |
| `arquivo` | Arquivo salvo em `media/documentos/` |
| `content_type` | Tipo MIME informado no upload |
| `tamanho_bytes` | Tamanho do arquivo em bytes |
| `status` | `ENVIADO`, `EM_VALIDACAO`, `APROVADO`, `REPROVADO` ou `SUBSTITUIDO` |
| `versao` | Numero sequencial da versao do documento dentro do processo e tipo |
| `documento_anterior` | Documento substituido pela versao atual, quando houver |
| `validado_por` | Usuario administrativo que validou o documento |
| `validado_em` | Data e hora da validacao |
| `motivo_reprovacao` | Motivo informado quando o documento e reprovado |
| `observacoes` | Observacoes administrativas da validacao |
| `enviado_em` | Data e hora exata do envio |
