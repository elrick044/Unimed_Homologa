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
- `GET /api/processos/<id_processo>/minuta/download/`
- `POST /api/admin/processos/<id_processo>/parecer/`
- `POST /api/admin/documentos/<id_documento>/validar/`
- `GET /api/admin/config/usuarios/`
- `POST /api/admin/config/usuarios/`
- `GET /api/admin/config/usuarios/<id_usuario>/`
- `PUT /api/admin/config/usuarios/<id_usuario>/`
- `DELETE /api/admin/config/usuarios/<id_usuario>/`
- `GET /api/admin/config/documentos/`
- `POST /api/admin/config/documentos/`
- `GET /api/admin/config/documentos/<id_tipo_documento>/`
- `PUT /api/admin/config/documentos/<id_tipo_documento>/`
- `DELETE /api/admin/config/documentos/<id_tipo_documento>/`
- `GET /api/admin/config/fluxos/`
- `POST /api/admin/config/fluxos/`
- `GET /api/admin/config/fluxos/<id_fluxo>/`
- `PUT /api/admin/config/fluxos/<id_fluxo>/`
- `DELETE /api/admin/config/fluxos/<id_fluxo>/`
- `GET /api/admin/config/templates/`
- `POST /api/admin/config/templates/`
- `GET /api/admin/config/templates/<id_template>/`
- `PUT /api/admin/config/templates/<id_template>/`
- `DELETE /api/admin/config/templates/<id_template>/`

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
- Quando o processo entra em `EM_APROVACAO_INTERNA`, o backend cria automaticamente o fluxo sequencial de aprovacao interna.

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
  ],
  "fluxo_aprovacao": {
    "id": 1,
    "status": "EM_ANDAMENTO",
    "iniciado_em": "2026-05-10T10:40:00Z",
    "encerrado_em": null,
    "atualizado_em": "2026-05-10T10:40:00Z",
    "etapas": [
      {
        "id": 1,
        "aprovador": 20,
        "aprovador_email": "aprovador1@example.com",
        "aprovador_nome": "aprovador1@example.com",
        "ordem": 1,
        "status": "LIBERADO",
        "data_liberacao": "2026-05-10T10:40:00Z",
        "data_conclusao": null,
        "criado_em": "2026-05-10T10:40:00Z",
        "atualizado_em": "2026-05-10T10:40:00Z"
      },
      {
        "id": 2,
        "aprovador": 21,
        "aprovador_email": "aprovador2@example.com",
        "aprovador_nome": "aprovador2@example.com",
        "ordem": 2,
        "status": "AGUARDANDO",
        "data_liberacao": null,
        "data_conclusao": null,
        "criado_em": "2026-05-10T10:40:00Z",
        "atualizado_em": "2026-05-10T10:40:00Z"
      }
    ]
  },
  "pareceres": []
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

## GET /api/processos/<id_processo>/minuta/download/

Baixa o PDF da minuta gerada para o processo.

Requer autenticacao JWT. Prestadores acessam apenas a minuta do proprio processo; usuarios com perfil `EQUIPE_ADMINISTRATIVA` ou `ADMINISTRADOR` podem acessar minutas de qualquer processo.

### Headers

```http
Authorization: Bearer <access_token>
```

### Response 200

Retorna o arquivo PDF como download.

```http
Content-Type: application/pdf
Content-Disposition: attachment; filename="minuta_processo_1.pdf"
```

### Response 401

Retornado quando o token JWT esta ausente, invalido ou expirado.

### Response 403

Retornado quando o usuario nao possui acesso ao processo informado.

### Response 404

Retornado quando o processo nao existe ou ainda nao possui minuta gerada.

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

## POST /api/admin/processos/<id_processo>/parecer/

Emite um parecer na cadeia sequencial de aprovacao interna.

Apenas usuarios com perfil `EQUIPE_ADMINISTRATIVA` ou `ADMINISTRADOR` podem acessar. Alem disso, o usuario logado deve ser o aprovador da etapa atualmente `LIBERADO`.

### Headers

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Request

```json
{
  "decisao": "APROVADO",
  "observacoes": "Parecer favoravel para continuidade."
}
```

### Campos

| Campo | Tipo | Obrigatorio | Regra |
| --- | --- | --- | --- |
| `decisao` | string | Sim | Aceita `APROVADO` ou `REPROVADO` |
| `observacoes` | string | Nao | Texto livre usado tambem como motivo em caso de reprovacao |

### Response 201

```json
{
  "parecer": {
    "id": 1,
    "aprovador": 20,
    "aprovador_email": "aprovador1@example.com",
    "etapa": 1,
    "decisao": "APROVADO",
    "observacoes": "Parecer favoravel para continuidade.",
    "data_hora": "2026-05-26T10:00:00Z",
    "docusign_envelope_id": null,
    "docusign_recipient_id": null,
    "docusign_status": null,
    "docusign_assinado_em": null
  },
  "processo_status": "EM_APROVACAO_INTERNA",
  "fluxo_status": "EM_ANDAMENTO",
  "etapa_status": "CONCLUIDO",
  "proxima_etapa": 2
}
```

### Regras de Transicao

Quando `decisao = APROVADO`:

- A etapa atual passa para `CONCLUIDO`.
- `data_conclusao` da etapa atual e preenchida.
- A proxima etapa por ordem passa para `LIBERADO`.
- Se nao houver proxima etapa, o fluxo passa para `CONCLUIDO`, `encerrado_em` e preenchido e o processo passa para `APROVADO`.
- O historico recebe `Etapa de aprovacao liberada` ou `Processo aprovado`, conforme o caso.

Quando `decisao = REPROVADO`:

- A etapa atual passa para `CONCLUIDO`.
- O fluxo passa para `ENCERRADO` e `encerrado_em` e preenchido.
- O processo passa imediatamente para `REPROVADO`.
- O historico recebe `Processo reprovado` com o motivo em `metadados.motivo`.
- Todas as alteracoes ocorrem na mesma transacao de banco.

### Observabilidade

O backend registra logs estruturados para:

- `parecer_attempt`
- `parecer_blocked_order_or_user`
- `parecer_blocked_state`
- `parecer_success`
- `parecer_final_state_transition`

### Response 400

Retornado quando o processo ou fluxo nao esta em estado valido para receber parecer.

Exemplo:

```json
{
  "processo": [
    "Processo nao esta em aprovacao interna."
  ]
}
```

### Response 401

Retornado quando o token JWT esta ausente, invalido ou expirado.

### Response 403

Retornado quando o usuario nao e o aprovador da etapa liberada ou nao possui perfil administrativo.

Exemplo:

```json
{
  "detail": "Usuario nao possui etapa liberada para este processo."
}
```

## GET /api/admin/config/usuarios/

Lista usuarios internos. Requer perfil `ADMINISTRADOR`.

### Response 200

```json
{
  "usuarios": [
    {
      "id": 10,
      "email": "analista@example.com",
      "perfil": "EQUIPE_ADMINISTRATIVA",
      "first_name": "Ana",
      "last_name": "Silva",
      "nome": "Ana Silva",
      "is_active": true,
      "date_joined": "2026-05-27T10:00:00Z",
      "last_login": null
    }
  ]
}
```

## POST /api/admin/config/usuarios/

Cria usuario interno. Requer perfil `ADMINISTRADOR`.

### Request

```json
{
  "email": "analista@example.com",
  "perfil": "EQUIPE_ADMINISTRATIVA",
  "first_name": "Ana",
  "last_name": "Silva",
  "is_active": true,
  "password": "SenhaForte123"
}
```

### Regras

- `perfil` aceita apenas `EQUIPE_ADMINISTRATIVA` ou `ADMINISTRADOR`.
- `password` e obrigatorio na criacao.

### Response 201

Retorna o usuario criado, sem a senha.

## GET /api/admin/config/usuarios/<id_usuario>/

Detalha um usuario interno. Requer perfil `ADMINISTRADOR`.

## PUT /api/admin/config/usuarios/<id_usuario>/

Atualiza um usuario interno. Requer perfil `ADMINISTRADOR`.

### Request

```json
{
  "first_name": "Analista",
  "is_active": true
}
```

### Response 200

Retorna o usuario atualizado.

## DELETE /api/admin/config/usuarios/<id_usuario>/

Inativa logicamente um usuario interno, definindo `is_active=false`. Requer perfil `ADMINISTRADOR`.

### Response 204

Sem corpo.

## GET /api/admin/config/documentos/

Lista todos os tipos de documento, ativos e inativos. Requer perfil `ADMINISTRADOR`.

### Response 200

```json
{
  "documentos": [
    {
      "id": 1,
      "nome": "Contrato Social",
      "descricao": "Documento de constituicao da empresa.",
      "obrigatorio": true,
      "ativo": true,
      "criado_em": "2026-05-27T10:00:00Z",
      "atualizado_em": "2026-05-27T10:00:00Z"
    }
  ]
}
```

## POST /api/admin/config/documentos/

Cria um tipo de documento. Requer perfil `ADMINISTRADOR`.

### Request

```json
{
  "nome": "Licenca Sanitaria",
  "descricao": "Licenca sanitaria atualizada.",
  "obrigatorio": true,
  "ativo": true
}
```

### Response 201

Retorna o tipo criado.

## GET /api/admin/config/documentos/<id_tipo_documento>/

Detalha um tipo de documento. Requer perfil `ADMINISTRADOR`.

## PUT /api/admin/config/documentos/<id_tipo_documento>/

Atualiza nome, descricao, obrigatoriedade ou status ativo. Requer perfil `ADMINISTRADOR`.

### Request

```json
{
  "obrigatorio": false,
  "ativo": true
}
```

### Response 200

Retorna o tipo atualizado.

## DELETE /api/admin/config/documentos/<id_tipo_documento>/

Inativa logicamente um tipo de documento, definindo `ativo=false`. Requer perfil `ADMINISTRADOR`.

Observacao:

- Esta rota nao apaga documentos ja enviados. Documentos historicos permanecem vinculados ao tipo.

### Response 204

Sem corpo.

## GET /api/admin/config/fluxos/

Lista configuracoes de fluxo padrao. Requer perfil `ADMINISTRADOR`.

### Response 200

```json
{
  "fluxos": [
    {
      "id": 1,
      "nome": "Fluxo Padrao Assistencial",
      "ativo": true,
      "etapas": [
        {
          "id": 1,
          "aprovador": 20,
          "aprovador_email": "aprovador1@example.com",
          "aprovador_nome": "aprovador1@example.com",
          "ordem": 1
        }
      ],
      "criado_em": "2026-05-27T10:00:00Z",
      "atualizado_em": "2026-05-27T10:00:00Z"
    }
  ]
}
```

## POST /api/admin/config/fluxos/

Cria configuracao padrao da cadeia de aprovacao. Requer perfil `ADMINISTRADOR`.

### Request

```json
{
  "nome": "Fluxo Padrao Assistencial",
  "ativo": true,
  "etapas": [
    {
      "aprovador": 20,
      "ordem": 1
    },
    {
      "aprovador": 21,
      "ordem": 2
    }
  ]
}
```

### Regras

- Deve haver ao menos uma etapa.
- `aprovador` deve ser usuario ativo com perfil `EQUIPE_ADMINISTRATIVA`.
- `ordem` nao pode repetir dentro da mesma configuracao.
- O mesmo aprovador nao pode repetir dentro da mesma configuracao.
- Quando uma configuracao e criada ou atualizada como `ativo=true`, as demais configuracoes sao marcadas como `ativo=false`.

### Response 201

Retorna a configuracao criada.

## GET /api/admin/config/fluxos/<id_fluxo>/

Detalha uma configuracao de fluxo. Requer perfil `ADMINISTRADOR`.

## PUT /api/admin/config/fluxos/<id_fluxo>/

Atualiza nome, status ativo e substitui a lista de etapas quando `etapas` for enviada. Requer perfil `ADMINISTRADOR`.

### Request

```json
{
  "ativo": true,
  "etapas": [
    {
      "aprovador": 21,
      "ordem": 1
    },
    {
      "aprovador": 20,
      "ordem": 2
    }
  ]
}
```

### Response 200

Retorna a configuracao atualizada.

## DELETE /api/admin/config/fluxos/<id_fluxo>/

Inativa uma configuracao de fluxo, definindo `ativo=false`. Requer perfil `ADMINISTRADOR`.

### Response 204

Sem corpo.

## GET /api/admin/config/templates/

Lista templates de contrato, incluindo versoes inativas. Requer perfil `ADMINISTRADOR`.

### Response 200

```json
{
  "templates": [
    {
      "id": 2,
      "nome": "Contrato Prestador",
      "conteudo_html": "<h1>{{ razao_social }}</h1><p>CNPJ {{ cnpj }}</p>",
      "ativo": true,
      "versao": 2,
      "template_anterior": 1,
      "criado_em": "2026-06-03T10:00:00Z",
      "atualizado_em": "2026-06-03T10:00:00Z"
    }
  ]
}
```

## POST /api/admin/config/templates/

Cria um template de contrato. Requer perfil `ADMINISTRADOR`.

### Request

```json
{
  "nome": "Contrato Prestador",
  "conteudo_html": "<h1>{{ razao_social }}</h1><p>CNPJ {{ cnpj }}</p>",
  "ativo": true
}
```

### Response 201

Retorna o template criado. Quando criado como `ativo=true`, os demais templates ativos sao inativados.

## GET /api/admin/config/templates/<id_template>/

Detalha uma versao de template. Requer perfil `ADMINISTRADOR`.

## PUT /api/admin/config/templates/<id_template>/

Atualiza um template. Requer perfil `ADMINISTRADOR`.

### Regras de versionamento

- Se o template editado estiver ativo, a API cria uma nova versao com `versao` incrementada e `template_anterior` apontando para a versao anterior.
- A versao anterior e marcada como `ativo=false`.
- Minutas ja geradas continuam vinculadas ao `TemplateContrato` usado no momento da geracao.
- Se a nova versao for salva como `ativo=true`, os demais templates ativos sao inativados.

### Request

```json
{
  "conteudo_html": "<h1>{{ razao_social }}</h1><p>CNPJ {{ cnpj }}</p><p>{{ endereco }}</p>"
}
```

### Response 200

Retorna a nova versao do template quando o template anterior estava ativo.

## DELETE /api/admin/config/templates/<id_template>/

Inativa uma versao de template, definindo `ativo=false`. Requer perfil `ADMINISTRADOR`.

### Response 204

Sem corpo.

### Geracao automatica de minuta

Quando um processo chega ao status `APROVADO`, o sistema busca o `TemplateContrato` ativo mais recente, renderiza `conteudo_html` com os dados reais do prestador e salva um PDF em `MinutaContrato`.

Variaveis suportadas no template:

- `{{ razao_social }}`
- `{{ nome_fantasia }}`
- `{{ cnpj }}`
- `{{ endereco }}`
- `{{ nome_responsavel }}`
- `{{ email }}`
- `{{ telefone }}`
- `{{ processo_id }}`

Depois da geracao, o processo muda para `MINUTA_GERADA` e o historico recebe o evento `Minuta gerada`. Se nao houver template ativo, o processo permanece `APROVADO` e nenhuma minuta e criada.

### Observabilidade das Configuracoes

Mudancas administrativas registram logs estruturados com `actor_id`, estado anterior e novo estado quando aplicavel:

- `config_user_created`
- `config_user_updated`
- `config_user_deactivated`
- `config_document_type_created`
- `config_document_type_updated`
- `config_document_type_deactivated`
- `config_approval_flow_created`
- `config_approval_flow_updated`
- `config_approval_flow_deactivated`
- `config_contract_template_created`
- `config_contract_template_versioned`
- `config_contract_template_deactivated`

### Respostas de Permissao

Todas as rotas `/api/admin/config/...` retornam:

- `401` quando o token JWT esta ausente, invalido ou expirado.
- `403` quando o usuario autenticado nao possui perfil `ADMINISTRADOR`.

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
- Ao entrar em `EM_APROVACAO_INTERNA`, a cadeia padrao de aprovacao e criada automaticamente com os usuarios ativos de perfil `EQUIPE_ADMINISTRATIVA`, ordenados por `id`.
- A primeira etapa e criada com status `LIBERADO`; as demais com status `AGUARDANDO`.

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

### FluxoAprovacao

| Campo | Descricao |
| --- | --- |
| `processo` | Processo de homologacao vinculado ao fluxo |
| `status` | `EM_ANDAMENTO`, `CONCLUIDO` ou `ENCERRADO` |
| `iniciado_em` | Data de inicio do fluxo |
| `encerrado_em` | Data em que o fluxo foi concluido ou encerrado por reprovacao |
| `atualizado_em` | Data da ultima atualizacao |

Observacoes:

- Existe no maximo um fluxo por processo.
- O fluxo e criado automaticamente quando o processo entra em `EM_APROVACAO_INTERNA`.
- A configuracao padrao usa usuarios ativos com perfil `EQUIPE_ADMINISTRATIVA`, em ordem crescente de `id`.

### EtapaAprovacao

| Campo | Descricao |
| --- | --- |
| `fluxo` | Fluxo de aprovacao vinculado |
| `aprovador` | Usuario responsavel pela etapa |
| `ordem` | Posicao sequencial do aprovador |
| `status` | `AGUARDANDO`, `LIBERADO` ou `CONCLUIDO` |
| `data_liberacao` | Data em que a etapa foi liberada para parecer |
| `data_conclusao` | Data em que a etapa foi concluida |
| `criado_em` | Data de criacao |
| `atualizado_em` | Data da ultima atualizacao |

Regras:

- A ordem e unica dentro de cada fluxo.
- Um aprovador nao se repete dentro do mesmo fluxo.
- A primeira etapa da cadeia padrao inicia como `LIBERADO`.

### ParecerProcesso

| Campo | Descricao |
| --- | --- |
| `processo` | Processo avaliado |
| `aprovador` | Usuario que emitiu o parecer |
| `etapa` | Etapa de aprovacao relacionada, quando houver |
| `decisao` | `APROVADO` ou `REPROVADO` |
| `observacoes` | Texto livre do parecer |
| `data_hora` | Data e hora do parecer |
| `docusign_envelope_id` | Campo previsto para integracao futura com DocuSign |
| `docusign_recipient_id` | Campo previsto para integracao futura com DocuSign |
| `docusign_status` | Campo previsto para integracao futura com DocuSign |
| `docusign_assinado_em` | Campo previsto para integracao futura com DocuSign |

### ConfiguracaoFluxoPadrao

| Campo | Descricao |
| --- | --- |
| `nome` | Nome da configuracao padrao |
| `ativo` | Indica se a configuracao sera usada para novos fluxos |
| `criado_em` | Data de criacao |
| `atualizado_em` | Data da ultima atualizacao |

### EtapaConfiguracaoPadrao

| Campo | Descricao |
| --- | --- |
| `configuracao` | Configuracao de fluxo vinculada |
| `aprovador` | Usuario da equipe administrativa que aprovara nessa posicao |
| `ordem` | Ordem sequencial da etapa |

### TemplateContrato

| Campo | Descricao |
| --- | --- |
| `nome` | Nome administrativo do template |
| `conteudo_html` | HTML com variaveis renderizadas pela engine de templates do Django |
| `ativo` | Indica se a versao pode ser usada para novas minutas |
| `versao` | Numero da versao do template |
| `template_anterior` | Versao anterior quando criada por edicao de template ativo |
| `criado_em` | Data de criacao |
| `atualizado_em` | Data da ultima atualizacao |

Regras:

- Editar um template ativo cria uma nova versao e inativa a anterior.
- Minutas ja geradas permanecem vinculadas a versao usada originalmente.
- A API mantem apenas um template ativo por vez quando templates sao criados ou atualizados como ativos.

### MinutaContrato

| Campo | Descricao |
| --- | --- |
| `processo` | Processo de homologacao vinculado a minuta |
| `template` | Template e versao usados na geracao |
| `arquivo_pdf` | Arquivo PDF salvo em `media/minutas/` |
| `gerado_em` | Data e hora da geracao |

Regras:

- Existe no maximo uma minuta por processo.
- A minuta e gerada automaticamente quando o processo passa para `APROVADO` e existe template ativo.
- Apos a geracao, o processo passa para `MINUTA_GERADA`.

## Permissoes

As permissoes DRF customizadas seguem estas regras:

- Prestador acessa apenas processos cujo `prestador_empresa` pertence ao proprio usuario.
- Equipe Administrativa acessa processos para analise.
- Administrador acessa todos os processos e configuracoes administrativas.

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
