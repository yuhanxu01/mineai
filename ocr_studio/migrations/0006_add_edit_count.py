from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ocr_studio', '0005_alter_ocrpage_binary_image_and_more'),
    ]

    operations = [
        # Use SeparateDatabaseAndState because SQLite table rebuild would
        # enforce an incorrect UNIQUE constraint from the faked migration 0005.
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE ocr_studio_ocrusagequota ADD COLUMN edit_count INTEGER NOT NULL DEFAULT 0",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='ocrusagequota',
                    name='edit_count',
                    field=models.IntegerField(default=0, verbose_name='提交修改次数'),
                ),
            ],
        ),
    ]
