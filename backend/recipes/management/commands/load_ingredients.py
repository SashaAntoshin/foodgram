import csv
import os

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = "Load ingredients from CSV file"

    def handle(self, *args, **options):
        csv_file = "../data/ingredients.csv"

        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f"File {csv_file} not found"))
            return

        with open(csv_file, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            ingredients_created = 0

            for row in reader:
                if len(row) >= 2:
                    name = row[0].strip()
                    measurement_unit = row[1].strip()

                    ingredient, created = Ingredient.objects.get_or_create(
                        name=name, measurement_unit=measurement_unit
                    )
                    if created:
                        ingredients_created += 1
                        self.stdout.write(
                            f"Created: {name} - {measurement_unit}"
                        )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully loaded {ingredients_created} ingredients"
                )
            )
