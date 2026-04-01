from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('group_expenses', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupexpense',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='expenses', to='group_expenses.group'),
        ),
        migrations.AddField(
            model_name='groupexpense',
            name='split_type',
            field=models.CharField(default='equal', max_length=50),
        ),
        migrations.AddField(
            model_name='settlement',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='group_expenses.group'),
        ),
        migrations.AddField(
            model_name='settlement',
            name='expense',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='settlements', to='group_expenses.groupexpense'),
        ),
    ]
