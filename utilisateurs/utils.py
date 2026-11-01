from .models import JournalAudit


def journaliser(request, action, entite='', reference='', details=''):
    """Trace une opération sensible dans le journal d'audit."""
    utilisateur = getattr(request, 'user', None)
    if utilisateur is not None and not getattr(utilisateur, 'is_authenticated', False):
        utilisateur = None
    ip = None
    if request is not None:
        ip = request.META.get('REMOTE_ADDR')
    return JournalAudit.objects.create(
        utilisateur=utilisateur,
        action=action,
        entite=entite,
        reference=str(reference or ''),
        details=details,
        adresse_ip=ip,
    )
