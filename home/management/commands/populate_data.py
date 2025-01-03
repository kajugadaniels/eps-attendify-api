import random
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
from home.models import *

class Command(BaseCommand):
    help = 'Populate the database with fake data for Departments, Employees, and Fields.'

    def handle(self, *args, **kwargs):
        fake = Faker('en_US')  # Using a supported locale

        self.stdout.write(self.style.SUCCESS('Starting data population...'))

        # Populate Departments
        self.populate_departments(fake)

        # Populate Fields
        self.populate_fields(fake)

        # Populate Employees
        self.populate_employees(fake)

        self.stdout.write(self.style.SUCCESS('Data population completed successfully.'))

    def populate_departments(self, fake):
        departments = [
            'Crop Production',
            'Livestock Management',
            'Agricultural Engineering',
            'Pest Control',
            'Soil Science',
            'Agricultural Economics',
            'Horticulture',
            'Agronomy',
            'Aquaculture',
            'Agroforestry',
            'Agricultural Biotechnology',
            'Farm Machinery',
            'Irrigation Systems',
            'Dairy Production',
            'Organic Farming',
            'Greenhouse Management',
            'Agricultural Extension',
            'Post-Harvest Technology',
            'Veterinary Services',
            'Agricultural Policy'
        ]

        with transaction.atomic():
            for dept_name in departments:
                Department.objects.create(
                    name=dept_name,
                    day_salary=str(random.randint(50, 500))  # Adjust as per model field type
                )
        self.stdout.write(self.style.SUCCESS(f'Created {len(departments)} departments.'))

    def populate_fields(self, fake):
        RW_CITIES = [
            'Kigali', 'Butare', 'Gisenyi', 'Rubavu', 'Muhanga',
            'Rwamagana', 'Kibuye', 'Nyagatare', 'Gitarama', 'Musanze',
            'Rulindo', 'Kayonza', 'Nyanza', 'Huye', 'Rusizi',
            'Kirehe', 'Ngoma', 'Burera', 'Karongi', 'Nyamagabe',
            'Gasabo', 'Kicukiro', 'Gatsata', 'Nyarugenge',
            'Nyabihu', 'Kamonyi', 'Rutsiro', 'Nyabikenke'
        ]
        
        field_names = set()
        while len(field_names) < 30:
            city = random.choice(RW_CITIES)
            descriptor = fake.word().capitalize()
            field_name = f"{city} {descriptor}"
            field_names.add(field_name)

        with transaction.atomic():
            for name in field_names:
                Field.objects.create(
                    name=name,
                    address=fake.address()
                )
        self.stdout.write(self.style.SUCCESS(f'Created {len(field_names)} fields.'))

    def populate_employees(self, fake):
        num_employees = 100

        # Generate unique names
        names = set()
        while len(names) < num_employees:
            name = fake.name()
            names.add(name)

        names = list(names)

        # Generate unique phone numbers
        phone_prefixes = ['078', '072', '073']
        phone_numbers = set()
        while len(phone_numbers) < num_employees:
            prefix = random.choice(phone_prefixes)
            number = prefix + ''.join([str(random.randint(0, 9)) for _ in range(7)])
            phone_numbers.add(number)

        phone_numbers = list(phone_numbers)

        # Generate unique tag_ids
        tag_ids = random.sample(range(1, 1001), num_employees)

        # Generate unique NIDs (14-digit numbers)
        nids = set()
        while len(nids) < num_employees:
            nid = ''.join([str(random.randint(0, 9)) for _ in range(14)])
            nids.add(nid)

        nids = list(nids)

        # Generate unique RSSB numbers (6-digit numbers)
        rssb_numbers = set()
        while len(rssb_numbers) < num_employees:
            rssb = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            rssb_numbers.add(rssb)

        rssb_numbers = list(rssb_numbers)

        with transaction.atomic():
            for i in range(num_employees):
                name = names[i]
                unique_suffix = random.randint(1, 9999)  # To ensure uniqueness
                email = self.generate_email(name, unique_suffix)
                Employee.objects.create(
                    name=name,
                    email=email,
                    phone_number=phone_numbers[i],
                    address=fake.address(),
                    tag_id=str(tag_ids[i]),
                    nid=nids[i],
                    rssb_number=rssb_numbers[i]
                )
        self.stdout.write(self.style.SUCCESS(f'Created {num_employees} employees.'))

    def generate_email(self, name, unique_suffix):
        # Convert name to lowercase and replace spaces with dots
        parts = name.lower().split()
        if len(parts) >= 2:
            email = f"{parts[0]}.{parts[1]}{unique_suffix}@doe.co"
        else:
            email = f"{parts[0]}{unique_suffix}@example.co"
        return email
