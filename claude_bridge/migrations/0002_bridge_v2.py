from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('claude_bridge', '0001_initial'),
    ]

    operations = [
        # ── BridgeConnection: per-connection task defaults ──
        migrations.AddField(
            model_name='bridgeconnection',
            name='default_webhook_url',
            field=models.URLField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='bridgeconnection',
            name='default_permission_mode',
            field=models.CharField(default='default', max_length=20),
        ),
        migrations.AddField(
            model_name='bridgeconnection',
            name='default_priority',
            field=models.IntegerField(default=5),
        ),

        # ── BridgeSession: priority queue fields ──
        migrations.AddField(
            model_name='bridgesession',
            name='priority',
            field=models.IntegerField(default=5),
        ),
        migrations.AddField(
            model_name='bridgesession',
            name='webhook_url',
            field=models.URLField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='bridgesession',
            name='webhook_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='bridgesession',
            name='result_text',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='bridgesession',
            name='input_tokens',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='bridgesession',
            name='output_tokens',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='bridgesession',
            name='cost_usd',
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name='bridgesession',
            name='duration_seconds',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bridgesession',
            name='started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # Update bridge_version default
        migrations.AlterField(
            model_name='bridgeconnection',
            name='bridge_version',
            field=models.CharField(default='2.0', max_length=50),
        ),
    ]
