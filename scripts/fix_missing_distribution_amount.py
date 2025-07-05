from django.db import connection
from django.db.utils import ProgrammingError

def run():
    """
    Add missing distribution_amount column to transactions_loan table if it doesn't exist
    """
    print("Checking for missing distribution_amount column in transactions_loan table...")
    
    # Check if column exists
    with connection.cursor() as cursor:
        try:
            # Try to select the column to see if it exists
            cursor.execute("SELECT distribution_amount FROM transactions_loan LIMIT 1")
            print("Column already exists, no action needed.")
            return
        except ProgrammingError:
            print("Column is missing, adding it now...")
            
            # Add the column to the table
            cursor.execute("""
                ALTER TABLE transactions_loan 
                ADD COLUMN distribution_amount numeric(12,0) NOT NULL DEFAULT 0
                CHECK (distribution_amount >= 0::numeric)
            """)
            print("Column distribution_amount has been added successfully.")
            
            # Set the value based on principal_amount for existing records
            cursor.execute("""
                UPDATE transactions_loan
                SET distribution_amount = principal_amount
                WHERE distribution_amount = 0
            """)
            print("Existing records have been updated with principal_amount values.")
            
if __name__ == "__main__":
    run()