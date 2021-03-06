# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_init, post_save
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from sponsorship.managers import SponsorManager

BENEFIT_TEXT, BENEFIT_FILE, BENEFIT_WEB_LOGO, BENEFIT_SIMPLE = "text", "file", "web_logo", "simple"

BENEFIT_TYPE_CHOICES = [
    (BENEFIT_TEXT, _("Text")),
    (BENEFIT_FILE, _("File")),
    (BENEFIT_WEB_LOGO, _("Web Logo")),
    (BENEFIT_SIMPLE, _("Simple"))
]

@python_2_unicode_compatible
class SponsorLevel(models.Model):

    name = models.CharField(_("name"), max_length=100)
    order = models.IntegerField(_("order"), default=0)
    cost = models.PositiveIntegerField(_("cost"))
    description = models.TextField(_("description"), blank=True, help_text=_("This is private."))

    class Meta:
        ordering = ["order"]
        verbose_name = _("sponsor level")
        verbose_name_plural = _("sponsor levels")

    def __str__(self):
        return self.name

    def sponsors(self):
        return self.sponsor_set.filter(active=True).order_by("added")


@python_2_unicode_compatible
class Sponsor(models.Model):

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="sponsorships", verbose_name=_("applicant"), null=True
    )

    name = models.CharField(_("Sponsor Name"), max_length=100)
    external_url = models.URLField(_("external URL"))
    annotation = models.TextField(_("annotation"), blank=True)
    contact_name = models.CharField(_("Contact Name"), max_length=100)
    contact_email = models.EmailField(_(u"Contact Email"))
    level = models.ForeignKey(SponsorLevel, verbose_name=_("level"))
    added = models.DateTimeField(_("added"), default=datetime.datetime.now)
    active = models.BooleanField(_("active"), default=False)

    # Denormalization (this assumes only one logo)
    sponsor_logo = models.ForeignKey("SponsorBenefit", related_name="+", null=True, blank=True, editable=False)

    objects = SponsorManager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("sponsor")
        verbose_name_plural = _("sponsors")

    # def get_absolute_url(self):
    #     if self.active:
    #         return reverse("sponsor_detail", kwargs={"pk": self.pk})
    #     return reverse("sponsor_list")

    @property
    def website_logo(self):
        if self.sponsor_logo is None:
            benefits = self.sponsor_benefits.filter(
                benefit__type=BENEFIT_WEB_LOGO, upload__isnull=False)[:1]
            if benefits.count():
                if benefits[0].upload:
                    self.sponsor_logo = benefits[0]
                    self.save()
        return self.sponsor_logo.upload

    @property
    def listing_text(self):
        if not hasattr(self, "_listing_text"):
            self._listing_text = None
            # @@@ better than hard-coding a pk but still not good
            benefits = self.sponsor_benefits.filter(benefit__name="Sponsor Description")
            if benefits.count():
                self._listing_text = benefits[0].text
        return self._listing_text

    def reset_benefits(self):
        """
        Reset all benefits for this sponsor to the defaults for their
        sponsorship level.
        """
        level = None

        try:
            level = self.level
        except SponsorLevel.DoesNotExist:
            pass

        allowed_benefits = []
        if level:
            for benefit_level in level.benefit_levels.all():
                # Create all needed benefits if they don't exist already
                sponsor_benefit, created = SponsorBenefit.objects.get_or_create(
                    sponsor=self, benefit=benefit_level.benefit)

                # and set to default limits for this level.
                sponsor_benefit.max_words = benefit_level.max_words
                sponsor_benefit.other_limits = benefit_level.other_limits

                # and set to active
                sponsor_benefit.active = True

                # @@@ We don't call sponsor_benefit.clean here. This means
                # that if the sponsorship level for a sponsor is adjusted
                # downwards, an existing too-long text entry can remain,
                # and won't raise a validation error until it's next
                # edited.
                sponsor_benefit.save()

                allowed_benefits.append(sponsor_benefit.pk)

        # Any remaining sponsor benefits that don't normally belong to
        # this level are set to inactive
        self.sponsor_benefits.exclude(pk__in=allowed_benefits)\
            .update(active=False, max_words=None, other_limits="")

    def send_coordinator_emails(self):
        pass  # @@@ should this just be done centrally?


def _store_initial_level(sender, instance, **kwargs):
    if instance:
        instance._initial_level_id = instance.level_id
post_init.connect(_store_initial_level, sender=Sponsor)


def _check_level_change(sender, instance, created, **kwargs):
    if instance and (created or instance.level_id != instance._initial_level_id):
        instance.reset_benefits()
post_save.connect(_check_level_change, sender=Sponsor)




@python_2_unicode_compatible
class Benefit(models.Model):

    name = models.CharField(_("name"), max_length=100)
    description = models.TextField(_("description"), blank=True)
    type = models.CharField(_("type"), choices=BENEFIT_TYPE_CHOICES, max_length=10, default=BENEFIT_SIMPLE)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class BenefitLevel(models.Model):

    benefit = models.ForeignKey(Benefit, related_name="benefit_levels", verbose_name=_("benefit"))
    level = models.ForeignKey(SponsorLevel, related_name="benefit_levels", verbose_name=_("level"))

    # default limits for this benefit at given level
    max_words = models.PositiveIntegerField(_("max words"), blank=True, null=True)
    other_limits = models.CharField(_("other limits"), max_length=200, blank=True)

    class Meta:
        ordering = ["level"]

    def __str__(self):
        return "%s - %s" % (self.level, self.benefit)


@python_2_unicode_compatible
class SponsorBenefit(models.Model):

    sponsor = models.ForeignKey(Sponsor, related_name="sponsor_benefits", verbose_name=_("sponsor"))
    benefit = models.ForeignKey(Benefit, related_name="sponsor_benefits", verbose_name=_("benefit"))
    active = models.BooleanField(default=True)

    # Limits: will initially be set to defaults from corresponding BenefitLevel
    max_words = models.PositiveIntegerField(_("max words"), blank=True, null=True)
    other_limits = models.CharField(_("other limits"), max_length=200, blank=True)

    # Data: zero or one of these fields will be used, depending on the
    # type of the Benefit (text, file, or simple)
    text = models.TextField(_("text"), blank=True)
    upload = models.FileField(_("file"), blank=True, upload_to="sponsor_files")

    class Meta:
        ordering = ["-active"]

    def __str__(self):
        return "%s - %s" % (self.sponsor, self.benefit)

    def clean(self):
        num_words = len(self.text.split())
        if self.max_words and num_words > self.max_words:
            raise ValidationError(
                "Sponsorship level only allows for %s words, you provided %d." % (
                    self.max_words, num_words))

    def data_fields(self):
        """
        Return list of data field names which should be editable for
        this ``SponsorBenefit``, depending on its ``Benefit`` type.
        """
        if self.benefit.type == BENEFIT_FILE or self.benefit.type == BENEFIT_WEB_LOGO:
            return ["upload"]
        elif self.benefit.type == BENEFIT_TEXT:
            return ["text"]
        return []
