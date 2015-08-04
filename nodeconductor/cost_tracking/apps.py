from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models import signals

from nodeconductor.cost_tracking import handlers
from nodeconductor.structure import models as structure_models


class CostTrackingConfig(AppConfig):
    name = 'nodeconductor.cost_tracking'
    verbose_name = "NodeConductor Cost Tracking"

    def ready(self):
        PriceEstimate = self.get_model('PriceEstimate')
        DefaultPriceListItem = self.get_model('DefaultPriceListItem')

        signals.post_save.connect(
            handlers.make_autocalculate_price_estimate_invisible_on_manual_estimate_creation,
            sender=PriceEstimate,
            dispatch_uid=('nodeconductor.cost_tracking.handlers.'
                          'make_autocalculate_price_estimate_invisible_on_manual_estimate_creation')
        )

        signals.post_delete.connect(
            handlers.make_autocalculated_price_estimate_visible_on_manual_estimate_deletion,
            sender=PriceEstimate,
            dispatch_uid=('nodeconductor.cost_tracking.handlers.'
                          'make_autocalculated_price_estimate_visible_on_manual_estimate_deletion')
        )

        signals.pre_save.connect(
            handlers.make_autocalculate_price_estimate_invisible_if_manually_created_estimate_exists,
            sender=PriceEstimate,
            dispatch_uid=('nodeconductor.cost_tracking.handlers.'
                          'make_autocalculate_price_estimate_invisible_if_manually_created_estimate_exists')
        )

        for index, service in enumerate(structure_models.Service.get_all_models()):
            signals.post_save.connect(
                handlers.create_price_list_items_for_service,
                sender=service,
                dispatch_uid=(
                    'nodeconductor.cost_tracking.handlers.create_price_list_items_for_service_{}_{}'
                    .format(service.__name__, index))
            )

        signals.post_save.connect(
            handlers.change_price_list_items_if_default_was_changed,
            sender=DefaultPriceListItem,
            dispatch_uid='nodeconductor.cost_tracking.handlers.change_price_list_items_if_default_was_changed'
        )

        signals.post_delete.connect(
            handlers.delete_price_list_items_if_default_was_deleted,
            sender=DefaultPriceListItem,
            dispatch_uid='nodeconductor.cost_tracking.handlers.delete_price_list_items_if_default_was_deleted'
        )