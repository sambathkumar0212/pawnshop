from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import ProjectState

def fix_item_photos(apps, schema_editor):
    # Use raw SQL to check if column exists and add if missing
    schema_editor.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'transactions_loan' AND column_name = 'item_photos'
        ) THEN
            ALTER TABLE transactions_loan 
            ADD COLUMN item_photos JSONB DEFAULT '[]'::jsonb;
        END IF;
    END
    $$;
    """)

class Migration(migrations.Migration):
    dependencies = [
        ('transactions', '0018_fix_customer_face_capture'),
    ]

    operations = [
        migrations.RunPython(fix_item_photos),
    ]