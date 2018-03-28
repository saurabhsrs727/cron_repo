# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
from django.db import models
from cron_apps.myplex_user.models import User, ThirdpartySubscriber


class PayTMTransaction(models.Model):
    """
        Model related to PayTM transactions
    """
    ref_id = models.CharField(max_length=20, unique=True)  # ORDER_ID/REFID
    request_type = models.CharField(max_length=30, choices=(('SUBSCRIBE', 'PURCHASE'),
                                                            ('RENEW_SUBSCRIPTION', 'RENEWAL'),
                                                            ('REFUND', 'REFUND')))
    user = models.ForeignKey(User)
    status = models.CharField(max_length=20, null=True)
    mid = models.CharField(max_length=200)
    mob_no = models.CharField(max_length=12, null=True)
    subs_service_id = models.CharField(max_length=20, null=True)
    subs_amount_type = models.CharField(max_length=10, null=True)
    subs_frequency = models.PositiveIntegerField(null=True)
    subs_frequency_unit = models.CharField(max_length=10, null=True)
    subs_start_date = models.DateTimeField(null=True)
    subs_expiry_date = models.DateTimeField(null=True)
    resp_msg = models.TextField(null=True)
    gateway_name = models.CharField(max_length=20, null=True)
    payment_mode = models.CharField(max_length=20, null=True)
    bank_name = models.CharField(max_length=40, null=True)
    bank_trans_id = models.CharField(max_length=50, null=True)
    trans_date = models.DateTimeField(null=True)
    trans_amount = models.FloatField(null=True)
    trans_id = models.CharField(max_length=64, null=True)
    subscription_id = models.CharField(max_length=50, null=True)
    trans_type = models.CharField(max_length=20, null=True)
    refund_order_id = models.CharField(max_length=20, null=True)
    refund_amount = models.FloatField(null=True)
    refund_date = models.DateTimeField(null=True)
    refund_id = models.CharField(max_length=64, null=True)
    created_datetime = models.DateTimeField(auto_now_add=True)
    package_name = models.CharField(max_length=20, null=True)
    package_price = models.FloatField(null=True)
    coupon_code = models.CharField(max_length=20, null=True)
    retControlUrl = models.CharField(max_length=500, null=True)

    class Meta:
        db_table = 'myplex_paytm_subscription'

class ThirdPartyRenewal(models.Model):
    """
        Model related to PayTM subscription renewal
    """
    user_id = models.IntegerField(null=True)
    validity_start_date = models.DateTimeField()
    validity_end_date = models.DateTimeField()
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'myplex_thirdparty_renewal'

class PayTMSubscriptionStatus(models.Model):
    """
        Model related to PayTM subscription status
    """
    user = models.ForeignKey(User)
    status = models.CharField(max_length=64)
    order_id = models.CharField(max_length=64)
    plan_to_switch = models.CharField(max_length=64)
    thirdparty_subscriber = models.ForeignKey(ThirdpartySubscriber)
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'myplex_paytm_subs_status'
