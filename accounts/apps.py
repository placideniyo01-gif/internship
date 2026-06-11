from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals

        try:
            from django.contrib.auth.models import User

            if not User.objects.filter(username="admin").exists():
                User.objects.create_superuser(
                    username="byke04",
                    email="placidebyke04@gmail.com",
                    password="Placidebyke04@"
                )
                print("SUPERUSER CREATED")

        except Exception as e:
            print("SUPERUSER ERROR:", e)

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.signals