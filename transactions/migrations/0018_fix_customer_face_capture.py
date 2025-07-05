from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import ProjectState

def fix_customer_face_capture(apps, schema_editor):
    # Use raw SQL to check if column exists and add if missing
    schema_editor.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'transactions_loan' AND column_name = 'customer_face_capture'
        ) THEN
            ALTER TABLE transactions_loan 
            ADD COLUMN customer_face_capture TEXT NULL;
        END IF;
    END
    $$;
    """)

class Migration(migrations.Migration):
    dependencies = [
        ('transactions', '0016_alter_loan_processing_fee'),
    ]

    operations = [
        migrations.RunPython(fix_customer_face_capture),
    ]