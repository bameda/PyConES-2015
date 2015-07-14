# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from proposals.actions import export_as_csv_action
from proposals.models import ProposalSection, Proposal
from proposals.models import ProposalKind

admin.site.register(
    Proposal,
    list_display=[
        "id",
        "title",
        "speaker",
        "speaker_email",
        "kind",
        "audience_level",
        "paper",
        "cancelled",
    ],
    list_filter=[
        "kind__name",
        # "result__accepted",
    ],
    actions=[export_as_csv_action("CSV Export", fields=[
        "id",
        "title",
        "speaker",
        "speaker_email",
        "kind",
    ])]
)
admin.site.register(ProposalSection)
admin.site.register(ProposalKind)
