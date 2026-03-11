import re
from django.db import migrations

_CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff'
                      r'\u2e80-\u2eff\u31c0-\u31ef\u3200-\u32ff'
                      r'\uff00-\uffef]')
_ASCII_WORD_RE = re.compile(r'[a-zA-Z0-9]+')


def recalculate_word_counts(apps, schema_editor):
    Chapter = apps.get_model('novel', 'Chapter')
    to_update = []
    for ch in Chapter.objects.all():
        wc = len(_CJK_RE.findall(ch.content or '')) + len(_ASCII_WORD_RE.findall(ch.content or ''))
        if ch.word_count != wc:
            ch.word_count = wc
            to_update.append(ch)
    if to_update:
        Chapter.objects.bulk_update(to_update, ['word_count'])


class Migration(migrations.Migration):
    dependencies = [
        ('novel', '0002_project_user'),
    ]
    operations = [
        migrations.RunPython(recalculate_word_counts, migrations.RunPython.noop),
    ]
