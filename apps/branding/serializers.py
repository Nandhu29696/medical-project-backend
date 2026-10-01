from rest_framework import serializers

from apps.branding.models import PRESETS, SiteTheme, ThemePreset


class SiteThemeSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(
        source="updated_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = SiteTheme
        fields = (
            "preset",
            "primary_color",
            "accent_color",
            "heading_font",
            "body_font",
            "corner_style",
            "updated_by_name",
            "updated_at",
        )
        read_only_fields = ("updated_by_name", "updated_at")

    def validate(self, attrs):
        # Choosing a named preset fills in its values; editing any value makes it CUSTOM.
        preset = attrs.get("preset")
        if preset and preset != ThemePreset.CUSTOM:
            preset_values = PRESETS[preset]
            overrides = {k: v for k, v in attrs.items() if k in preset_values}
            if any(str(v).upper() != str(preset_values[k]).upper() for k, v in overrides.items()):
                attrs["preset"] = ThemePreset.CUSTOM
            else:
                attrs.update(preset_values)
        elif preset is None and attrs:
            attrs["preset"] = ThemePreset.CUSTOM
        for field in ("primary_color", "accent_color"):
            if field in attrs:
                attrs[field] = attrs[field].upper()
        return attrs


class PublicThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteTheme
        fields = (
            "preset",
            "primary_color",
            "accent_color",
            "heading_font",
            "body_font",
            "corner_style",
            "updated_at",
        )
