import csv

from pathlib import Path
from rich import print
from datetime import datetime

from database import Expense, MonthlyLog, Bucket, Tag

CSV_HEADER = ["description", "bucket", "tags", "date", "amount"]


def expense_from_csv_row(session, user_config, row):
    if len(row) != len(CSV_HEADER):
        raise ValueError(f"Expected {len(CSV_HEADER)} columns, found {len(row)}")
    row = list(map(lambda c: c.strip(), row))
    data = dict(
        description=row[0] if len(row[0]) > 0 else None,
        bucket=row[1],
        tags=set(map(lambda t: t.strip(), row[2].split(",")))
        if len(row[2]) > 0
        else set(),
        date=datetime.strptime(row[3], "%Y-%m-%d").date(),
        amount=float(row[4]),
    )
    log = MonthlyLog.get_or_create(
        session, data["date"].month, data["date"].year, user_config
    )
    try:
        data["bucket"] = Bucket[data["category"]]
    except KeyError as e:
        raise ValueError(f"Category {data['bucket']} does not exist")

    tags = []
    for tag in data["tags"]:
        q = session.query(Tag).filter(Tag.name == tag)
        if q.count() == 0:
            raise ValueError(f"Tag `{tag}` doesn't exist")
        tags.append(q.first())
    data["tags"] = tags

    return Expense(log=log, **data)


class CSVExpenseImporter:
    def __init__(self, filepath: str):
        self.file = Path(filepath)

    def file_exists(self):
        return self.file.is_file()

    def write_sample_file(self):
        if self.file_exists():
            print("Warning: Overwrote import file")
        with open(self.file, "w") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(CSV_HEADER)

    def import_to(self, session, user_config):
        with open(self.file, "r") as f:
            reader = csv.reader(f, delimiter=";")
            # skip header
            next(reader)
            num_successful_imports = 0
            failed_imports = []

            for i, row in enumerate(reader):
                try:
                    session.add(expense_from_csv_row(session, user_config, row))
                    num_successful_imports += 1
                except ValueError as e:
                    print(f"Unable to import row {i+2}: {str(e)}")
                    failed_imports.append(row)
            session.commit()
            with open(self.file, "w") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(CSV_HEADER)
                writer.writerows(failed_imports)

            print(
                f"Looked at {num_successful_imports+len(failed_imports)} rows. Failed to import {len(failed_imports)}."
            )
