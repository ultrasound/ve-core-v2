import logging

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.lru_cache import lru_cache
from jsonfield import JSONField
from model_utils import FieldTracker

from nodeconductor.core import models as core_models
from nodeconductor.cost_tracking import managers, CostConstants
from nodeconductor.structure import models as structure_models


logger = logging.getLogger(__name__)


class PriceEstimate(core_models.UuidMixin, models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    scope = GenericForeignKey('content_type', 'object_id')

    total = models.FloatField(default=0)
    details = JSONField(blank=True)

    month = models.PositiveSmallIntegerField(validators=[MaxValueValidator(12), MinValueValidator(1)])
    year = models.PositiveSmallIntegerField()

    is_manually_input = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)

    objects = managers.PriceEstimateManager('scope')

    class Meta:
        unique_together = ('content_type', 'object_id', 'month', 'year', 'is_manually_input')

    @classmethod
    @lru_cache(maxsize=1)
    def get_estimated_models(self):
        return (
            structure_models.Resource.get_all_models() +
            structure_models.ServiceProjectLink.get_all_models() +
            structure_models.Service.get_all_models() +
            [structure_models.Project, structure_models.Customer]
        )

    @classmethod
    @lru_cache(maxsize=1)
    def get_editable_estimated_models(self):
        return (
            structure_models.Resource.get_all_models() +
            structure_models.ServiceProjectLink.get_all_models()
        )

    def __str__(self):
        return '%s for %s-%s' % (self.scope, self.year, self.month)


class AbstractPriceListItem(models.Model):
    class Meta:
        abstract = True

    key = models.CharField(max_length=50)
    value = models.DecimalField(default=0, max_digits=16, decimal_places=8)
    units = models.CharField(max_length=30, blank=True)
    item_type = models.CharField(max_length=30,
                                 choices=CostConstants.PriceItem.CHOICES,
                                 default=CostConstants.PriceItem.FLAVOR)


class DefaultPriceListItem(core_models.UuidMixin, AbstractPriceListItem):
    """ Default price list item for all resources of supported service types """
    resource_content_type = models.ForeignKey(ContentType, default=None)

    tracker = FieldTracker()


class PriceListItem(core_models.UuidMixin, AbstractPriceListItem):
    # Generic key to service
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    service = GenericForeignKey('content_type', 'object_id')
    resource_content_type = models.ForeignKey(ContentType, related_name='+', default=None)

    is_manually_input = models.BooleanField(default=False)

    objects = managers.PriceListItemManager('service')

    class Meta:
        unique_together = ('key', 'content_type', 'object_id')


class ResourceUsage(core_models.UuidMixin):
    date = models.DateField()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    resource = GenericForeignKey('content_type', 'object_id')

    units = models.CharField(max_length=30, blank=True)
    value = models.DecimalField(default=0, max_digits=16, decimal_places=8)

    class Meta:
        unique_together = ('date', 'content_type', 'object_id', 'units')
