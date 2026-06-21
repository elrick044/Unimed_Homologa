from rest_framework.permissions import BasePermission

from .models import ProcessoHomologacao, User


class IsPrestadorProcessOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        processo = obj if isinstance(obj, ProcessoHomologacao) else getattr(obj, 'processo', None)
        prestador = getattr(request.user, 'prestador_empresa', None)
        return bool(prestador and processo and processo.prestador_id == prestador.id)


class IsAdministrativeTeam(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.perfil in (User.Perfil.EQUIPE_ADMINISTRATIVA, User.Perfil.ADMINISTRADOR)
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsSystemAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.perfil == User.Perfil.ADMINISTRADOR
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class CanAccessProcess(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            IsAdministrativeTeam().has_permission(request, view)
            or IsPrestadorProcessOwner().has_object_permission(request, view, obj)
        )
