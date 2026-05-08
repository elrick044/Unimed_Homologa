from django.db import migrations


DEFAULT_DOCUMENT_TYPES = [
    ('Contrato Social', 'Documento de constituicao da empresa.'),
    ('Comprovante de Endereco', 'Comprovante atualizado do endereco informado.'),
    ('Alvara de Funcionamento', 'Alvara ou licenca de funcionamento vigente.'),
    ('Certidao Negativa', 'Certidao negativa aplicavel ao processo de homologacao.'),
]


def create_default_document_types(apps, schema_editor):
    TipoDocumento = apps.get_model('core', 'TipoDocumento')

    for nome, descricao in DEFAULT_DOCUMENT_TYPES:
        TipoDocumento.objects.update_or_create(
            nome=nome,
            defaults={
                'descricao': descricao,
                'obrigatorio': True,
                'ativo': True,
            },
        )


def remove_default_document_types(apps, schema_editor):
    TipoDocumento = apps.get_model('core', 'TipoDocumento')
    TipoDocumento.objects.filter(nome__in=[nome for nome, _ in DEFAULT_DOCUMENT_TYPES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_tipodocumento_documentoprestador'),
    ]

    operations = [
        migrations.RunPython(create_default_document_types, remove_default_document_types),
    ]
