"""
    Contains PayTM related utilities
"""
import urllib
import urllib2
import json
import datetime
import string
import random
import logging
from django.utils import timezone

from cron_apps.paytm.Checksum import generate_checksum, verify_checksum, generate_refund_checksum
from cron_apps.paytm.models import *
from cron_apps.myplex_user.models import ThirdpartySubscriber
from django.conf import settings
PAYTM_SETTINGS = settings.PAYTM_SETTINGS
LOGGER = logging.getLogger("myplex_service.cron_apps.paytm.paytm_utils")


class PayTMAPIs(object):
    """
        Class for PayTM related APIs
    """

    def __init__(self):
        """
            Will initialize PAYTM SETTINGS
        """
        self.MID = PAYTM_SETTINGS['MID']
        self.CHANNEL_ID = PAYTM_SETTINGS['CHANNEL_ID']
        self.INDUSTRY_TYPE_ID = PAYTM_SETTINGS['INDUSTRY_TYPE_ID']
        self.WEBSITE = PAYTM_SETTINGS['WEBSITE']
        self.CALLBACK_URL = PAYTM_SETTINGS['CALLBACK_URL']
        self.MERCHANT_KEY = PAYTM_SETTINGS['MERCHANT_KEY']
        self.PAYTM_TRANS_REQ_URL = PAYTM_SETTINGS['TRANS_REQ_URL']
        self.PAYTM_TRANS_STATUS_URL = PAYTM_SETTINGS['TRANS_STATUS_URL']
        self.PAYTM_REFUND_URL = PAYTM_SETTINGS['REFUND_URL']
        self.PACKS_SETTINGS = PAYTM_SETTINGS['PACKS_SETTINGS']
        self.SUBS_EXPIRY_DATE = PAYTM_SETTINGS['SUBS_EXPIRY_DATE']

    def get_package_conf(self, package_name):
        """
        
        :param package_name: 
        :return: return Package configuration for frequency and frequency unit  
        """
        return self.PACKS_SETTINGS[package_name.lower()]

    def subscribe_trans_req_url(self, order_type, trans_amount, subs_max_amount,
                                cust_id, subs_amount_type,
                                subs_days, start_date,
                                retControlUrl, package_name, package_price):
        """
            Will create transaction request URL
        """
        ORDER_ID = self.id_generator(order_type)
        subs_service_id = self.id_generator('SERVICE_ID')
        package_conf = self.get_package_conf(package_name)
        subs_frequency = package_conf['subs_frequency']
        subs_frequency_unit = package_conf['subs_frequency_unit']
        if start_date:
            start_date_obj = datetime.datetime.strptime(start_date, '%m-%d-%Y_%H:%M:%S')
            subs_type = 'switch'
        else:
            start_date_obj = datetime.datetime.now()
            subs_type = 'new'
        subs_expiry_date_obj = datetime.datetime.strptime(self.SUBS_EXPIRY_DATE, '%Y-%m-%d')
        params = {'REQUEST_TYPE': 'SUBSCRIBE',
                  'ORDER_ID': ORDER_ID,
                  'MID': self.MID,
                  'CUST_ID': cust_id,
                  'TXN_AMOUNT': trans_amount,
                  'SUBS_MAX_AMOUNT': subs_max_amount,
                  'CHANNEL_ID': self.CHANNEL_ID,
                  'INDUSTRY_TYPE_ID': self.INDUSTRY_TYPE_ID,
                  'WEBSITE': self.WEBSITE,
                  'SUBS_SERVICE_ID': subs_service_id,
                  'SUBS_AMOUNT_TYPE': subs_amount_type,
                  'SUBS_FREQUENCY': subs_frequency,
                  'SUBS_FREQUENCY_UNIT': subs_frequency_unit,
                  'SUBS_ENABLE_RETRY': 0,
                  'SUBS_EXPIRY_DATE': subs_expiry_date_obj.strftime('%Y-%m-%d'),
                  'SUBS_PPI_ONLY': 'Y',
                  'CALLBACK_URL': self.CALLBACK_URL}

        if subs_type == 'switch':
            # start_date = datetime.datetime.strptime(start_date, '%m-%d-%Y_%H:%M:%S')
            # start_date = datetime.datetime.strftime(start_date, '%Y-%m-%d')
            params.update({
                'SUBS_START_DATE': start_date_obj.strftime('%Y-%m-%d'),
                'SUBS_GRACE_DAYS': int(subs_frequency)-1,
            })
        checksum_hash = generate_checksum(params, self.MERCHANT_KEY)
        params['CHECKSUMHASH'] = checksum_hash

        self.log_new_subscribe_trans(ref_id=ORDER_ID,
                                     retControlUrl=retControlUrl,
                                     trans_amount=trans_amount,
                                     user=cust_id,
                                     request_type='SUBSCRIBE',
                                     subs_amount_type=subs_amount_type,
                                     subs_frequency=subs_frequency,
                                     subs_frequency_unit=subs_frequency_unit,
                                     subs_start_date=start_date_obj if subs_type == 'switch' else None,
                                     subs_expiry_date=subs_expiry_date_obj,
                                     subs_service_id=subs_service_id,
                                     package_name=package_name,
                                     package_price=package_price)
        LOGGER.info("Paytm transaction URL: %s", self.PAYTM_TRANS_REQ_URL
                    + '?' + urllib.urlencode(params))
        return self.PAYTM_TRANS_REQ_URL + '?' + urllib.urlencode(params)

    def verify_checksum(self, data, checksum_hash):
        """
            This will verify checksum hash

        """
        return verify_checksum(data, self.MERCHANT_KEY, checksum_hash)

    def id_generator(self, order_type, size=10, chars=string.ascii_uppercase + string.digits):
        prefix = ''
        if order_type == 'SUBSCRIBE':
            prefix = 'SB'
        elif order_type == 'RENEW_SUBSCRIPTION':
            prefix = 'RN'
        elif order_type == 'REFUND':
            prefix = 'RF'
        elif order_type == 'SERVICE_ID':
            prefix = 'SSID'
        return prefix + ''.join(random.choice(chars) for _ in range(size))

    def trans_status_response(self, order_id):
        """
            Will get the transaction status response for ORDER_ID
        """
        req_data = {"MID": self.MID, "ORDERID": order_id}
        checksum_hash = generate_checksum(req_data, self.MERCHANT_KEY)
        req_data['CHECKSUMHASH'] = checksum_hash
        params = {'JsonData': json.dumps(req_data)}
        url = self.PAYTM_TRANS_STATUS_URL + '?' + urllib.urlencode(params)
        LOGGER.info("Paytm transaction status URL: %s", url)
        status_req = urllib2.urlopen(url)
        status_resp = status_req.read()
        LOGGER.info("Paytm transaction status response: %s",json.loads(status_resp))
        return status_req.code, json.loads(status_resp)

    def subs_renew_trans_req_url(self, trans_amount, order_id):
        """
            Will create transaction request URL for subscription renew
        """
        today = datetime.datetime.today()
        log_obj = PayTMTransaction.objects.get(ref_id=order_id)
        status_obj = PayTMSubscriptionStatus.objects.get(order_id=order_id, thirdparty_subscriber__user_activated=1)
        start_date = status_obj.thirdparty_subscriber.validity_end_date
        ORDER_ID = self.id_generator('RENEW_SUBSCRIPTION')
        params = {'REQUEST_TYPE': 'RENEW_SUBSCRIPTION',
                  'ORDER_ID': ORDER_ID,
                  'MID': self.MID,
                  'TXN_AMOUNT': trans_amount,
                  'SUBS_ID': log_obj.subscription_id,
                  'CALLBACK_URL': self.CALLBACK_URL}
        checksum_hash = generate_checksum(params, self.MERCHANT_KEY)
        params['CHECKSUMHASH'] = checksum_hash

        self.log_new_subscribe_trans(ref_id=ORDER_ID,
                                     retControlUrl=log_obj.retControlUrl,
                                     trans_amount=trans_amount,
                                     user=log_obj.cust_id,
                                     request_type='RENEW_SUBSCRIPTION',
                                     subs_amount_type=log_obj.subs_amount_type,
                                     subs_frequency=log_obj.subs_frequency,
                                     subs_frequency_unit=log_obj.subs_frquency_unit,
                                     subs_expiry_date=log_obj.subs_expiry_date,
                                     subs_start_date=start_date,
                                     subs_service_id=log_obj.subs_service_id,
                                     package_name=log_obj.package_name,
                                     package_price=log_obj.package_price
                                     )

        LOGGER.info("Paytm transaction renewal URL: %s",
                    self.PAYTM_TRANS_REQ_URL + '?' + urllib.urlencode(params))
        return self.PAYTM_TRANS_REQ_URL + '?' + urllib.urlencode(params)

    def refund_subscription(self, order_id, refund_id, trans_id, refund_amount, comments=''):
        req_data = {'TXNTYPE': 'REFUND',
                    'TXNID': str(trans_id),
                    'ORDERID': str(order_id),
                    'MID': str(self.MID),
                    'REFUNDAMOUNT': str(refund_amount),
                    # 'COMMENTS': comments,
                    'REFID': str(refund_id)}
        checksum_hash = generate_refund_checksum(req_data, self.MERCHANT_KEY)
        req_data['CHECKSUM'] = checksum_hash
        params = {'JsonData': json.dumps(req_data)}
        url = self.PAYTM_REFUND_URL + '?' + urllib.urlencode(params)
        LOGGER.info("Paytm refund subscription URL: %s", url)
        status_req = urllib2.urlopen(url)
        status_resp = status_req.read()
        LOGGER.info("Paytm transaction status response: %s",json.loads(status_resp))
        return status_req.code, json.loads(status_resp)

    def refund_status_response(self, order_id, refund_id):
        """
            Will get the refund status response for ORDER_ID
        """
        req_data = {"MID": self.MID, "ORDERID": order_id, 'REFID': refund_id}
        checksum_hash = generate_checksum(req_data, self.MERCHANT_KEY)
        req_data['CHECKSUMHASH'] = checksum_hash
        params = {'JsonData': json.dumps(req_data)}
        url = self.PAYTM_REFUND_URL + '?' + urllib.urlencode(params)
        status_req = urllib2.urlopen(url)
        return status_req.code, json.loads(status_req.read())

    # Logging functions for PayTMTransaction model
    def log_new_subscribe_trans(self, user, ref_id, trans_amount, subs_service_id,
                                subs_amount_type, subs_frequency, subs_frequency_unit,
                                subs_expiry_date, subs_start_date, request_type,
                                retControlUrl, package_name, package_price):
        """
        :param user:
        :param ref_id:
        :param trans_amount:
        :return: This will log new subscribe transaction
        """
        log_obj = PayTMTransaction()
        log_obj.ref_id = ref_id
        log_obj.user_id = user
        log_obj.retControlUrl = retControlUrl
        log_obj.request_type = request_type
        log_obj.mid = self.MID
        log_obj.trans_amount = trans_amount
        log_obj.subs_service_id = subs_service_id
        log_obj.subs_amount_type = subs_amount_type
        log_obj.subs_frequency = subs_frequency
        log_obj.subs_frequency_unit = subs_frequency_unit
        log_obj.subs_expiry_date = subs_expiry_date
        log_obj.subs_start_date = subs_start_date
        log_obj.package_name = package_name
        log_obj.package_price = package_price
        log_obj.save()
        LOGGER.info("New entry added in myplex_paytm_subscription for subscription")

    def update_subscribe_log(self, ref_id, status, resp_msg, gateway_name,
                             payment_mode, bank_name, bank_trans_id,
                             trans_date, trans_id, subscription_id, trans_type,
                             refund_amount):
        """
            Function for updating existing log after transaction status call
        """
        log_obj = PayTMTransaction.objects.get(ref_id=ref_id)
        if log_obj.request_type == 'SUBSCRIBE' or log_obj.request_type == 'RENEW_SUBSCRIPTION':
            log_obj.gateway_name = gateway_name
            log_obj.status = status
            log_obj.resp_msg = resp_msg
            log_obj.payment_mode = payment_mode
            log_obj.bank_name = bank_name
            log_obj.bank_trans_id = bank_trans_id
            log_obj.trans_date = datetime.datetime.strptime(trans_date, '%Y-%m-%d %H:%M:%S.%f')
            log_obj.trans_id = trans_id
            log_obj.subscription_id = subscription_id
            log_obj.trans_type = trans_type
            log_obj.refund_amount = refund_amount
            log_obj.save()
            LOGGER.info("log updated in myplex_paytm_subscription")

    def insert_third_party(self, user_id, start_date, end_date, package_id):
        """
            Function for updating existing third party model
        """
        thirdParty_obj = ThirdpartySubscriber()
        thirdParty_obj.user_activation_mode = 'ok'

        thirdParty_obj.user_id = user_id
        thirdParty_obj.validity_start_date = start_date
        thirdParty_obj.validity_end_date = end_date
        thirdParty_obj.package_id = package_id
        thirdParty_obj.partner_id = 99
        thirdParty_obj.user_activated = 1
        thirdParty_obj.partner_name = 'paytm'
        thirdParty_obj.save()
        LOGGER.info("Entry updated for user in myplex_thirdparty_subscriber")
        return  thirdParty_obj

    def insert_third_party_renewal(self, user_id, start_date, end_date):
        """
        :param user_id:
        :param start_date:
        :param end_date:
        :return:
        """
        third_party_renewal = ThirdPartyRenewal()
        third_party_renewal.user_id = user_id
        third_party_renewal.validity_start_date = start_date
        third_party_renewal.validity_end_date = end_date
        third_party_renewal.save()
        LOGGER.info("Entry updated for user in myplex_thirdparty_renewal")

    def insert_paytm_subs_status(self, user_id, status, order_id, plan_to_switch,
                                 third_party_obj):
        """
        :param user:
        :param subs_frequency:
        :return:
        """
        paytm_subs_status = PayTMSubscriptionStatus()
        paytm_subs_status.user = user_id
        paytm_subs_status.status = status
        paytm_subs_status.order_id = order_id
        paytm_subs_status.thirdparty_subscriber = third_party_obj
        paytm_subs_status.plan_to_switch = plan_to_switch
        paytm_subs_status.save()
        LOGGER.info("New entry added in myplex_paytm_subs_status")

    def log_refund_request(self, ref_id, user, mob_no, trans_id,
                           refund_order_id, refund_amount, refund_id,
                           resp_msg, status, gateway_name, trans_amount):
        """
        :param user:
        :param ref_id:
        :param trans_amount:
        :return: This will log new subscribe transaction
        """
        log_obj = PayTMTransaction()
        log_obj.ref_id = ref_id
        log_obj.user = user
        log_obj.mob_no = mob_no
        log_obj.request_type = 'REFUND'
        log_obj.mid = self.MID
        log_obj.status = status
        log_obj.trans_amount = trans_amount
        log_obj.gateway_name = gateway_name
        log_obj.resp_msg = resp_msg
        log_obj.trans_id = trans_id
        log_obj.refund_order_id = refund_order_id
        log_obj.refund_amount = refund_amount
        log_obj.refund_id = refund_id
        log_obj.save()
        LOGGER.info("New entry added in myplex_paytm_subscription for refund")
        return log_obj

    def update_refund_log(self, ref_id, status, resp_msg, gateway_name,
                          payment_mode, bank_trans_id,trans_date, trans_id,
                          refund_date):
        """
            Function for updating existing log after transaction status call
        """
        log_obj = PayTMTransaction.objects.get(ref_id=ref_id)
        if log_obj.request_type == 'REFUND':
            log_obj.gateway_name = gateway_name
            log_obj.status = status
            log_obj.resp_msg = resp_msg
            log_obj.payment_mode = payment_mode
            log_obj.bank_trans_id = bank_trans_id
            log_obj.trans_date = datetime.datetime.strptime(trans_date, '%Y-%m-%d %H:%M:%S.%f')
            log_obj.trans_id = trans_id
            log_obj.refund_date = datetime.datetime.strptime(refund_date, '%Y-%m-%d %H:%M:%S.%f')
            log_obj.save()
            LOGGER.info("log updated in myplex_paytm_subscription")

    def cancel_old_paytm_subs(self, user_id):
        """
            Will cancel old paytm subscription
        """
        today_dt = timezone.now()
        active_paytm = ThirdpartySubscriber.objects.filter(user_id=user_id,
                                                           partner_id=99,
                                                           user_activated=1,
                                                           validity_start_date__lte=today_dt,
                                                           validity_end_date__gte=today_dt)
        active_paytm_ids = active_paytm.values_list('id', flat=True)
        active_paytm.update(user_activated=3, cancellation_date=today_dt)
        PayTMSubscriptionStatus.objects.filter(thirdparty_subscriber__in=active_paytm_ids,
                                               user=user_id).update(status='Unsubscribe')

    def refund_request_process(self, paytm_st):
        """

        :param paytm_st: paytm status table obj
        :return: This function will make refund request on realtime
        """
        refund_obj = PayTMTransaction.objects.filter(status='TXN_SUCCESS',
                                                     ref_id=paytm_st.order_id).first()
        REFUND_ID = ''
        if refund_obj:
            thirdparty_obj = paytm_st.thirdparty_subscriber
            REFUND_ID = 'RF' + self.id_generator(6)
            refund_amount = self.amount_calc(refund_obj, thirdparty_obj)
            LOGGER.info('Calculated Refund amount %s', refund_amount)
            if refund_amount > 0:
                LOGGER.info('Sending refund request.')
                st, data = self.refund_subscription(order_id=refund_obj.ref_id,
                                                     refund_amount=refund_amount,
                                                     trans_id=str(refund_obj.trans_id),
                                                     refund_id=REFUND_ID,
                                                     comments='')
                LOGGER.info('New refund response %s, %s', st, json.dumps(data))
                log_obj = self.log_refund_request(ref_id=REFUND_ID,
                                                 refund_order_id=refund_obj.ref_id,
                                                 refund_amount=data.get('REFUNDAMOUNT'),
                                                 trans_id=data.get('TXNID'),
                                                 resp_msg=data.get('RESPMSG'),
                                                 status=data.get('STATUS'),
                                                 trans_amount=data.get('TXNAMOUNT'),
                                                 gateway_name=data.get('GATEWAY'),
                                                 refund_id=data.get('REFUNDID'),
                                                 user=refund_obj.user,
                                                 mob_no=None)
                if st == 200:
                    if data.get('STATUS'):
                        if data['STATUS'] == 'TXN_SUCCESS':
                            paytm_st.status = 'Refund'
                            paytm_st.save()
                            LOGGER.info('New refund request completed sucessfully: %s', REFUND_ID)
                        else:
                            LOGGER.info('New refund request completed with status: %s  %s', REFUND_ID, data['STATUS'])
                    else:
                        log_obj.resp_msg = json.dumps(data)
                        log_obj.save()
                        LOGGER.info('New refund request unsuccessful: %s', REFUND_ID)
            else:
                paytm_st.status = 'Refund'
                paytm_st.save()
        return REFUND_ID

    def amount_calc(self, trans_obj, thirdparty_obj):
        """

        :param trans_obj:
        :param thirdparty_obj:
        :return: Will calculate amount to be refunded
        """
        retained_amount = 50
        refund_amount = 0
        package_name = thirdparty_obj.package_id
        if thirdparty_obj.validity_start_date > thirdparty_obj.cancellation_date:
            refund_amount = trans_obj.trans_amount
        else:
            time_diff = thirdparty_obj.validity_start_date - thirdparty_obj.cancellation_date
            no_days = time_diff.days
            if package_name == 'Quarterly':
                if no_days <= 30:
                    refund_amount = trans_obj.trans_amount - retained_amount
                elif no_days <= 60:
                    refund_amount = trans_obj.trans_amount - retained_amount * 2
            elif package_name == 'Annual':
                if no_days <= 30:
                    refund_amount = trans_obj.trans_amount - retained_amount
                elif no_days <= 60:
                    refund_amount = trans_obj.trans_amount - retained_amount * 2
                elif no_days <= 90:
                    refund_amount = trans_obj.trans_amount - retained_amount * 3
                elif no_days <= 120:
                    refund_amount = trans_obj.trans_amount - retained_amount * 4
                elif no_days <= 150:
                    refund_amount = trans_obj.trans_amount - retained_amount * 5
                elif no_days <= 180:
                    refund_amount = trans_obj.trans_amount - retained_amount * 6
        return refund_amount
