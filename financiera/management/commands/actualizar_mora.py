from django.core.management.base import BaseCommand

from financiera.services.mora import actualizar_estados_mora


class Command(BaseCommand):
    help = 'Marca como VENCIDO las cuotas vencidas y pone en EN_MORA los préstamos correspondientes.'

    def handle(self, *args, **options):
        total = actualizar_estados_mora()
        self.stdout.write(self.style.SUCCESS(f'{total} préstamo(s) actualizado(s) a EN_MORA.'))
