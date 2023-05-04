import argparse
import csv
from datetime import datetime
import json


class ExpenseGrabber:
    def __init__(
        self,
        monthly_costs: list[str],
        categories: dict[str, str],
        interactive: bool = False,
    ) -> None:
        self._transactions: list[tuple[datetime, str, str, float]] = []
        self.MONTHLY_COSTS = monthly_costs
        self.categories = categories
        self.interactive = interactive

    def parse_rbc(self, file: str, month: int) -> None:
        """
        Process the RBC csv file and add the transactions to the transactions list
        :param file: The file name of the csv file
        :param month: The month you want to filter by
        """
        with open(file, newline="") as csvfile:
            data = csv.reader(csvfile, delimiter=",", quotechar='"')
            for row in data:
                if row[6] == "CAD$":
                    continue

                date = datetime.strptime(row[2], "%m/%d/%Y")

                category = self.categories.get(row[4], "Unknown")

                if category == "Unknown" and self.interactive:
                    self.add_category(row[4])
                    category = self.categories.get(row[4], "Unknown")
                else:
                    self.categories[row[4]] = category

                if (
                    date.month == month
                    and float(row[6]) < 0
                    and all(s not in row[4] for s in self.MONTHLY_COSTS)
                ):
                    self._transactions.append((date, row[4], category, float(row[6])))

    def parse_tangerine(self, file: str, month: int) -> None:
        """
        Process the Tangerine csv file and add the transactions to the transactions list
        :param file: The file name of the csv file
        :param month: The month you want to filter by
        """
        with open(file, newline="") as csvfile:
            data = csv.reader(csvfile, delimiter=",", quotechar='"')
            for row in data:
                if row[0] == "Transaction date":
                    continue

                date = datetime.strptime(row[0], "%m/%d/%Y")

                category = self.categories.get(row[2], "Unknown")
                if category == "Unknown":
                    category = row[3].split(":")[-1].strip()
                    if category == "" and self.interactive:
                        self.add_category(row[2])
                        category = self.categories.get(row[2], "Unknown")
                    else:
                        category = "Unknown"
                    self.categories[row[2]] = category

                if date.month == month and row[1] == "DEBIT":
                    self._transactions.insert(
                        0, (date, row[2], category, float(row[4]))
                    )

    def write_csv(self, file: str) -> None:
        """
        Write the transactions to a csv file
        :param file: The file name of the csv file
        """
        with open(file=file, mode="w") as output_file:
            writer = csv.writer(output_file)
            for transaction in self._transactions:
                data = (
                    transaction[0].strftime("%B %d, %Y"),
                    *transaction[1:],
                )
                writer.writerow(data)

    def process_transactions(
        self,
        banks: list[str],
        files: list[str],
        date: datetime,
        output_file: str | None = None,
    ) -> None:
        """
        Process the transactions from the banks and write them to a csv file
        :param banks: The banks you want to filter by
        :param files: The file names of the csv files
        :param date: The month you want to filter by
        :param output_file (optional): The file name of the csv file
        """
        if output_file is None:
            output_file = f"{date.strftime('%B-%Y')}.csv"

        for file, bank in enumerate(banks):
            match bank:
                case "rbc":
                    self.parse_rbc(files[file], date.month)
                case "tangerine":
                    self.parse_tangerine(files[file], date.month)
        self._transactions.sort(key=lambda transaction: transaction[0])
        self.write_csv(output_file)


    def total_spent(self) -> float:
        """
        Calculate the total amount spent
        """
        total = 0
        for transaction in self._transactions:
            total += transaction[3]
        return abs(total)

    def add_category(self, transaction: str) -> None:
        """
        Add a category to the categories dict
        :param transaction: The transaction you want to add a category to
        """
        unique_categories = self.get_unique_categories()
        print(f"Transaction: {transaction} has no category, please add one")
        print(
            "you can use the following categories or add your own (use the number to select)"
        )
        print(
            "\n".join(
                [f"{i}: {category}" for i, category in enumerate(unique_categories)]
            )
        )

        category = input("Category: ")
        try:
            self.categories[transaction] = unique_categories[int(category)]
            print(f"Added {transaction} to {unique_categories[int(category)]}")
        except:
            self.categories[transaction] = category
            print(f"Added {transaction} to new {category} category")

    def get_unique_categories(self) -> list[str]:
        """
        Get a list of unique categories
        """
        return list(set(self.categories.values()))

    def get_categories(self) -> dict[str, str]:
        """
        Get the categories dict
        """
        return self.categories


# Functions for script
def get_categories() -> dict[str, str]:
    """
    Get the categories from the json file
    """
    try:
        with open("categories.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_categories(categories: dict[str, str]) -> None:
    """
    Save the categories to the json file
    :param categories: The categories dict
    """
    with open("categories.json", "w") as file:
        json.dump(categories, file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file", help="The file name of the csv file(s), comma separated"
    )
    parser.add_argument("--date", help="The date you want to filter by (MM/YY))")
    parser.add_argument(
        "--bank", help="The bank(s) the csv file(s) are related to, comma separated"
    )
    args = parser.parse_args()

    banks = args.bank.split(",")
    files = args.file.split(",")

    date = datetime.strptime(args.date, "%m/%y")

    categories = get_categories()

    expense_grabber = ExpenseGrabber(
        monthly_costs=[],
        categories=categories,
        interactive=True,
    )
    expense_grabber.process_transactions(banks, files, date)

    print(f"Total spent: {expense_grabber.total_spent()}")
    print()
    print("Total spent by category:")
    for category in expense_grabber.get_unique_categories():
        total = 0
        for transaction in expense_grabber._transactions:
            if transaction[2] == category:
                total += transaction[3]
        print(f"{category}: {abs(round(total, 2))}")


    print("saving categories")
    save_categories(expense_grabber.get_categories())
