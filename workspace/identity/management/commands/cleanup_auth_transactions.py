from django.core.management.base import BaseCommand

from identity.services.transactions import cleanup_expired_transactions


class Command(BaseCommand):
    help = 'Delete expired Workspaces OAuth authorization transactions.'

    def handle(self, *args, **options):
        deleted, _ = cleanup_expired_transactions()
        self.stdout.write(f'Deleted {deleted} expired authorization transaction(s).')
