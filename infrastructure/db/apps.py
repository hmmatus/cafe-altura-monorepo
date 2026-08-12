from django.apps import AppConfig


class DbConfig(AppConfig):
    """Persistence app.

    The label is pinned rather than derived from the package path: migrations record the app
    label, so letting Django infer it would mean a package rename silently orphans the whole
    migration history.
    """

    name = "infrastructure.db"
    label = "db"
    default_auto_field = "django.db.models.BigAutoField"
