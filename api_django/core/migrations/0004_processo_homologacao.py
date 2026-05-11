import django.db.models.deletion
from django.db import migrations, models


STATUS_CHOICES = [
    ('CADASTRO_INICIADO', 'Cadastro iniciado'),
    ('DOCUMENTACAO_PENDENTE', 'Documentacao pendente'),
    ('EM_VALIDACAO', 'Em validacao'),
    ('CORRECAO_SOLICITADA', 'Correcao solicitada'),
    ('EM_APROVACAO_INTERNA', 'Em aprovacao interna'),
    ('REPROVADO', 'Reprovado'),
    ('APROVADO', 'Aprovado'),
    ('MINUTA_GERADA', 'Minuta gerada'),
    ('PROCESSO_CONCLUIDO', 'Processo concluido'),
]


def create_processos_for_existing_prestadores(apps, schema_editor):
    PrestadorEmpresa = apps.get_model('core', 'PrestadorEmpresa')
    ProcessoHomologacao = apps.get_model('core', 'ProcessoHomologacao')
    HistoricoProcesso = apps.get_model('core', 'HistoricoProcesso')
    DocumentoPrestador = apps.get_model('core', 'DocumentoPrestador')

    for prestador in PrestadorEmpresa.objects.all():
        processo, created = ProcessoHomologacao.objects.get_or_create(
            prestador=prestador,
            defaults={'status': 'CADASTRO_INICIADO'},
        )

        if created:
            HistoricoProcesso.objects.create(
                processo=processo,
                acao='Cadastro criado',
                descricao='Processo de homologacao criado para prestador existente.',
                usuario=prestador.user,
            )

        DocumentoPrestador.objects.filter(prestador=prestador, processo__isnull=True).update(processo=processo)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_seed_tipos_documento'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessoHomologacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=STATUS_CHOICES, default='CADASTRO_INICIADO', max_length=30)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('concluido_em', models.DateTimeField(blank=True, null=True)),
                ('prestador', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='processo_homologacao', to='core.prestadorempresa')),
            ],
            options={
                'verbose_name': 'Processo de Homologacao',
                'verbose_name_plural': 'Processos de Homologacao',
                'ordering': ('-criado_em',),
            },
        ),
        migrations.CreateModel(
            name='HistoricoProcesso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acao', models.CharField(max_length=150)),
                ('descricao', models.TextField(blank=True)),
                ('metadados', models.JSONField(blank=True, default=dict)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('processo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historico', to='core.processohomologacao')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eventos_processo', to='core.user')),
            ],
            options={
                'verbose_name': 'Historico do Processo',
                'verbose_name_plural': 'Historicos dos Processos',
                'ordering': ('-criado_em',),
            },
        ),
        migrations.AddField(
            model_name='documentoprestador',
            name='processo',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='documentos', to='core.processohomologacao'),
        ),
        migrations.RunPython(create_processos_for_existing_prestadores, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='documentoprestador',
            name='processo',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documentos', to='core.processohomologacao'),
        ),
    ]
