# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib import admin

from sponsorship.models import BenefitLevel, SponsorLevel, Sponsor, Benefit
from sponsorship.models import SponsorBenefit


class BenefitLevelInline(admin.TabularInline):
    model = BenefitLevel
    extra = 0


class SponsorBenefitInline(admin.StackedInline):
    model = SponsorBenefit
    extra = 0
    fieldsets = [
        (None, {
            "fields": [
                ("benefit", "active"),
                ("max_words", "other_limits"),
                "text",
                "upload",
            ]
        })
    ]


class SponsorAdmin(admin.ModelAdmin):

    save_on_top = True
    fieldsets = [
        (None, {
            "fields": [
                ("name", "applicant"),
                ("level", "active"),
                "external_url",
                "annotation",
                ("contact_name", "contact_email")
            ]
        }),
        ("Metadata", {
            "fields": ["added"],
            "classes": ["collapse"]
        })
    ]
    inlines = [SponsorBenefitInline]
    list_display = ["name", "external_url", "level", "active"]

    def get_form(self, *args, **kwargs):
        # @@@ kinda ugly but using choices= on NullBooleanField is broken
        form = super(SponsorAdmin, self).get_form(*args, **kwargs)
        form.base_fields["active"].widget.choices = [
            (u"1", "unreviewed"),
            (u"2", "approved"),
            (u"3", "rejected")
        ]
        return form


class BenefitAdmin(admin.ModelAdmin):

    list_display = ["name", "type", "description"]
    inlines = [BenefitLevelInline]


class SponsorLevelAdmin(admin.ModelAdmin):

    inlines = [BenefitLevelInline]


admin.site.register(SponsorLevel, SponsorLevelAdmin)
admin.site.register(Sponsor, SponsorAdmin)
admin.site.register(Benefit, BenefitAdmin)
