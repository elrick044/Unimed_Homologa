import re

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import PrestadorEmpresa, User


CNPJ_FORMAT_RE = re.compile(r'^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$')


def normalize_cnpj(value):
    return re.sub(r'\D', '', value or '')


def validate_cnpj_format(value):
    if not CNPJ_FORMAT_RE.match(value or ''):
        raise serializers.ValidationError('CNPJ deve estar no formato 00.000.000/0000-00 ou conter 14 digitos.')

    digits = normalize_cnpj(value)
    if len(digits) != 14:
        raise serializers.ValidationError('CNPJ deve conter 14 digitos.')

    return digits


class PrestadorRegisterSerializer(serializers.Serializer):
    razao_social = serializers.CharField(max_length=255)
    nome_fantasia = serializers.CharField(max_length=255)
    cnpj = serializers.CharField(max_length=18)
    endereco = serializers.CharField()
    nome_responsavel = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    telefone = serializers.CharField(max_length=20)
    senha = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    def validate_cnpj(self, value):
        cnpj = validate_cnpj_format(value)

        if PrestadorEmpresa.objects.filter(cnpj=cnpj).exists():
            raise serializers.ValidationError('Ja existe um prestador cadastrado com este CNPJ.')

        return cnpj

    def validate_email(self, value):
        email = value.lower()

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError('Ja existe um usuario cadastrado com este e-mail.')

        return email

    def validate_senha(self, value):
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('senha')
        email = validated_data['email']

        user = User.objects.create_user(
            email=email,
            password=password,
            perfil=User.Perfil.PRESTADOR,
        )
        prestador = PrestadorEmpresa.objects.create(user=user, **validated_data)
        return prestador


class PrestadorEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrestadorEmpresa
        fields = (
            'id',
            'razao_social',
            'nome_fantasia',
            'cnpj',
            'endereco',
            'nome_responsavel',
            'email',
            'telefone',
            'criado_em',
            'atualizado_em',
        )
        read_only_fields = ('id', 'criado_em', 'atualizado_em')


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    senha = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        email = attrs.get('email', '').lower()
        password = attrs.get('senha')
        request = self.context.get('request')
        user = authenticate(request=request, username=email, password=password)

        if not user:
            raise serializers.ValidationError('E-mail ou senha invalidos.')

        if not user.is_active:
            raise serializers.ValidationError('Usuario inativo.')

        attrs['user'] = user
        return attrs
