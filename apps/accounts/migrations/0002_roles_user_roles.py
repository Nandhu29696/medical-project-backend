import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

ROLES = [
    ("SUPER_ADMIN", "Super Admin", "Full system access, including user and role management."),
    ("ADMIN", "Admin", "Operational administrator: manages CRM, products, doctors and patients."),
    ("SALES_MANAGER", "Sales Manager", "Manages campaigns and assigns leads to sales executives."),
    ("SALES_EXECUTIVE", "Sales Executive", "Works leads and follow-ups assigned to them."),
    ("DOCTOR", "Doctor", "Views assigned patients and records consultations."),
    ("PATIENT", "Patient", "Views own profile, consultations and assigned doctor."),
]


def seed_roles_and_copy_user_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    UserRole = apps.get_model("accounts", "UserRole")
    User = apps.get_model("accounts", "User")

    roles = {}
    for code, name, description in ROLES:
        roles[code], _ = Role.objects.get_or_create(
            code=code, defaults={"name": name, "description": description}
        )

    for user in User.objects.all():
        if user.role in roles:
            UserRole.objects.get_or_create(user=user, role=roles[user.role])


def copy_user_roles_back(apps, schema_editor):
    UserRole = apps.get_model("accounts", "UserRole")
    User = apps.get_model("accounts", "User")
    for user_role in UserRole.objects.select_related("role"):
        User.objects.filter(pk=user_role.user_id).update(role=user_role.role.code)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "code",
                    models.CharField(
                        choices=[
                            ("SUPER_ADMIN", "Super Admin"),
                            ("ADMIN", "Admin"),
                            ("SALES_MANAGER", "Sales Manager"),
                            ("SALES_EXECUTIVE", "Sales Executive"),
                            ("DOCTOR", "Doctor"),
                            ("PATIENT", "Patient"),
                        ],
                        max_length=32,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=64)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "roles", "ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="UserRole",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="user_roles",
                        to="accounts.role",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_roles",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "user_roles"},
        ),
        migrations.AddConstraint(
            model_name="userrole",
            constraint=models.UniqueConstraint(fields=("user", "role"), name="unique_user_role"),
        ),
        migrations.RunPython(seed_roles_and_copy_user_roles, copy_user_roles_back),
        migrations.RemoveField(model_name="user", name="role"),
        migrations.AddField(
            model_name="user",
            name="roles",
            field=models.ManyToManyField(
                blank=True,
                related_name="users",
                through="accounts.UserRole",
                through_fields=("user", "role"),
                to="accounts.role",
            ),
        ),
    ]
