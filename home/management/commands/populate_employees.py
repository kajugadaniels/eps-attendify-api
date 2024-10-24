from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.utils import IntegrityError
from home.models import *
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Populates the database with fake employees.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--number', type=int, help='Indicates the number of employees to be created.'
        )

    def handle(self, *args, **kwargs):
        fake = Faker()
        number = kwargs.get('number') or 50  # Default to creating 10 employees

        created_count = 0
        for _ in range(number):
            name = fake.name()
            nid = fake.unique.random_int(min=1000000000000, max=9999999999999)
            email = fake.unique.email()
            tag_id = fake.unique.lexify(text='??????????')
            phone_number = fake.unique.phone_number()
            address = fake.address()

            try:
                Employee.objects.create(
                    name=name,
                    nid=nid,
                    email=email,
                    tag_id=tag_id,
                    phone_number=phone_number,
                    address=address,
                )
                created_count += 1
            except IntegrityError as e:
                self.stdout.write(self.style.ERROR(f'Error creating employee {name}: {e}'))
                continue

        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} fake employees.'))
