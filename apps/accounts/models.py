import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models, transaction


class RoleCode(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
    ADMIN = "ADMIN", "Admin"
    SALES_MANAGER = "SALES_MANAGER", "Sales Manager"
    SALES_EXECUTIVE = "SALES_EXECUTIVE", "Sales Executive"
    DOCTOR = "DOCTOR", "Doctor"
    PATIENT = "PATIENT", "Patient"


# Highest privilege first. A user's primary `role` is the first of their roles in this list.
ROLE_PRIORITY = [
    RoleCode.SUPER_ADMIN,
    RoleCode.ADMIN,
    RoleCode.SALES_MANAGER,
    RoleCode.SALES_EXECUTIVE,
    RoleCode.DOCTOR,
    RoleCode.PATIENT,
]

ROLE_DESCRIPTIONS = {
    RoleCode.SUPER_ADMIN: "Full system access, including user and role management.",
    RoleCode.ADMIN: "Operational administrator: manages CRM, products, doctors and patients.",
    RoleCode.SALES_MANAGER: "Manages campaigns and assigns leads to sales executives.",
    RoleCode.SALES_EXECUTIVE: "Works leads and follow-ups assigned to them.",
    RoleCode.DOCTOR: "Views assigned patients and records consultations.",
    RoleCode.PATIENT: "Views own profile, consultations and assigned doctor.",
}


class Role(models.Model):
    code = models.CharField(max_length=32, unique=True, choices=RoleCode.choices)
    name = models.CharField(max_length=64)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "roles"
        ordering = ["id"]

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """Join table between users and roles (a user may hold several roles)."""

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="user_roles")
    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_roles"
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="unique_user_role"),
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.role.code}"


def get_role(code):
    role, _ = Role.objects.get_or_create(
        code=code,
        defaults={"name": RoleCode(code).label, "description": ROLE_DESCRIPTIONS.get(code, "")},
    )
    return role


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, role=None, roles=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        with transaction.atomic(using=self._db):
            user.save(using=self._db)
            codes = list(roles or [])
            if role and role not in codes:
                codes.insert(0, role)
            user.set_roles(codes)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", RoleCode.SUPER_ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    roles = models.ManyToManyField(
        Role,
        through=UserRole,
        through_fields=("user", "role"),
        related_name="users",
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def role_codes(self):
        """Role codes held by this user, highest privilege first (cached per instance)."""
        if not hasattr(self, "_role_codes"):
            if self._state.adding:
                return []
            held = set(self.roles.values_list("code", flat=True))
            self._role_codes = [code.value for code in ROLE_PRIORITY if code in held]
        return self._role_codes

    @property
    def role(self):
        codes = self.role_codes
        return codes[0] if codes else None

    def has_role(self, *codes):
        return any(code in self.role_codes for code in codes)

    def set_roles(self, codes, assigned_by=None):
        """Replace this user's roles with exactly `codes`."""
        codes = list(dict.fromkeys(codes))
        with transaction.atomic():
            self.user_roles.exclude(role__code__in=codes).delete()
            existing = set(self.user_roles.values_list("role__code", flat=True))
            for code in codes:
                if code not in existing:
                    UserRole.objects.create(user=self, role=get_role(code), assigned_by=assigned_by)
        self.__dict__.pop("_role_codes", None)

    def add_role(self, code, assigned_by=None):
        self.set_roles([*self.role_codes, code], assigned_by=assigned_by)

    @property
    def is_super_admin(self):
        return self.has_role(RoleCode.SUPER_ADMIN)

    @property
    def is_admin(self):
        return self.has_role(RoleCode.SUPER_ADMIN, RoleCode.ADMIN)

    @property
    def is_sales_manager(self):
        return self.role == RoleCode.SALES_MANAGER

    @property
    def is_sales_executive(self):
        return self.role == RoleCode.SALES_EXECUTIVE

    @property
    def is_doctor(self):
        return self.has_role(RoleCode.DOCTOR)

    @property
    def is_patient(self):
        return self.has_role(RoleCode.PATIENT)
