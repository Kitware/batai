import csv

from django.core.management.base import BaseCommand
from django.db import transaction

from bats_ai.core.models import GRTSCells


class Command(BaseCommand):
    help = 'Import data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument(
            '--batch-size', type=int, default=500, help='Batch size for database insertion'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        batch_size = options['batch_size']
        model_fields = {field.name for field in GRTSCells._meta.get_fields()}

        # Boolean field conversion map
        bool_map = {'true': True, 'false': False}

        # Track existing records
        existing_records = set(GRTSCells.objects.values_list('id', flat=True))

        records_to_create = []
        counter = 0

        with open(csv_file) as file:
            reader = csv.DictReader(file)

            for _index, row in enumerate(reader, start=1):
                filtered_row = {
                    key: (row[key] if row[key] != '' else None)
                    for key in row
                    if key in model_fields
                }

                # Convert boolean fields
                for boolean_field in ['priority_frame', 'priority_state', 'clipped']:
                    if boolean_field in filtered_row and filtered_row[boolean_field] is not None:
                        filtered_row[boolean_field] = bool_map.get(
                            filtered_row[boolean_field].lower(), None
                        )
                        if filtered_row[boolean_field] is None:
                            self.stderr.write(
                                'Invalid boolean value for field'
                                f' {boolean_field}: {row[boolean_field]}'
                            )
                            continue

                # Skip if record already exists
                if hash(tuple(filtered_row.items())) in existing_records:
                    continue

                records_to_create.append(GRTSCells(**filtered_row))
                counter += 1

                if len(records_to_create) >= batch_size:
                    with transaction.atomic():
                        GRTSCells.objects.bulk_create(records_to_create, ignore_conflicts=True)
                    records_to_create = []

                self.stdout.write(f'Processed {counter} rows')

            # Insert remaining records
            if records_to_create:
                with transaction.atomic():
                    GRTSCells.objects.bulk_create(records_to_create, ignore_conflicts=True)

        self.stdout.write('Import completed successfully')
