# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from markupfield.widgets import MarkupTextarea

from modeltranslation.forms import TranslationModelForm

from core.helpers.generators import random_string
from proposals.models import Proposal
from speakers.models import Speaker


class ProposalFrom(TranslationModelForm):

    speaker_name = forms.CharField(
        label=_("Nombre del ponente"),
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    speaker_email = forms.EmailField(
        label=_("Email del ponente"),
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = Proposal
        exclude = ["speaker", "additional_speakers", "cancelled",
                   "additional_notes_markup_type", "abstract_markup_type",
                   "additional_notes_es_markup_type", "abstract_es_markup_type",
                   "additional_notes_en_markup_type", "abstract_en_markup_type",
                   ]
        widgets = {
            "kind": forms.Select(attrs={"class": "form-control"}),
            "audience_level": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control"}),
            "abstract": MarkupTextarea(attrs={"class": "form-control"}),
            "additional_notes": MarkupTextarea(attrs={"class": "form-control"}),
        }

    def clean_abstract(self):
        abstract = self.cleaned_data["abstract"]
        words = "".join(character if character.isalnum() else " " for character in abstract).split()
        if len(words) < 80:
            raise forms.ValidationError(_("¡El resumen es demasiado corto! Ayuda al equipo organizador a seleccionar "
                                          "tu charla indicando un breve esquema, si habrá demos en directo o qué "
                                          "conocimientos previos debería tener la audiencia"))
        return abstract

    def get_speaker(self):
        name = self.cleaned_data.get("speaker_name", "")
        email = self.cleaned_data.get("speaker_email")
        try:
            speaker = Speaker.objects.get(user__email=email)
        except Speaker.DoesNotExist:
            user = User.objects.create_user(
                username=random_string(), email=email, first_name=name, password=random_string()
            )
            speaker = Speaker.objects.create(
                user=user, name=name,
                biography="", biography_markup_type='markdown',
                biography_es="", biography_es_markup_type='markdown',
                biography_en="", biography_en_markup_type='markdown'
            )
        return speaker

    def save(self, commit=True):
        proposal = super(ProposalFrom, self).save(commit=False)
        proposal.speaker = self.get_speaker()
        proposal.abstract_markup_type = 'markdown'
        proposal.abstract_es_markup_type = 'markdown'
        proposal.abstract_en_markup_type = 'markdown'
        proposal.additional_notes_markup_type = 'markdown'
        proposal.additional_notes_es_markup_type = 'markdown'
        proposal.additional_notes_en_markup_type = 'markdown'
        proposal.save()
        return proposal
