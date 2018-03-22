from django.utils import timezone
from cron_apps.paytm.models import *
from cron_apps.paytm.paytm_utils import PayTMAPIs
import logging
import json
LOGGER = logging.getLogger(__name__)


class PaytmCronsUtils(object):
    """
        Cron utility functions
    """

    retained_amount = 50
    refund_to_process = 1

    def refund_script(self, *args, **options):
        """

        :param args:
        :param options:
        :return: Script will refund the unsettled amount
        """
        today = timezone.now()
        paytm_obj = PayTMAPIs()
        # today_start = datetime.datetime.combine(today, datetime.time.min)
        paytm_status_objs = PayTMSubscriptionStatus.objects.filter(status='Unsubscribe',
                                                                   thirdparty_subscriber__user_activated=3,
                                                                   modified_on__lte=today).order_by('-modified_on')[: self.refund_to_process]
        for obj in paytm_status_objs:
            LOGGER.info('=======================%s=========================', obj.order_id)
            refund_obj = PayTMTransaction.objects.filter(status='TXN_SUCCESS',
                                                         ref_id=obj.order_id).first()
            thirdparty_obj = obj.thirdparty_subscriber
            if refund_obj:
                new_request = True
                pre_requests = PayTMTransaction.objects.filter(request_type='REFUND',
                                                               refund_order_id=obj.order_id)
                succ_req = pre_requests.filter(status='TXN_SUCCESS')
                pending_req = pre_requests.filter(status='PENDING').order_by('-created_datetime').first()
                if succ_req:
                    new_request = False
                    LOGGER.info('Already Refunded.')
                elif pending_req:
                    req = pending_req
                    refund_status, status_data = paytm_obj.refund_status_response(req.ref_id, req.refund_id)
                    LOGGER.info('Pending refund status check %s, %s', refund_status, json.dumps(status_data))
                    if refund_status == 200:
                        if status_data.get('STATUS'):
                            paytm_obj.update_refund_log(ref_id=req.ref_id,
                                                        status=status_data.get('STATUS'),
                                                        resp_msg=status_data.get('RESPMSG'),
                                                        gateway_name=status_data.get('GATEWAY'),
                                                        payment_mode=status_data.get('PAYMENTMODE'),
                                                        bank_trans_id=status_data.get('BANKTXNID'),
                                                        trans_date=status_data.get('TXNDATE'),
                                                        trans_id=status_data.get('TXNID'),
                                                        refund_date=status_data.get('REFUNDDATE'))
                            if status_data['STATUS'] == 'TXN_SUCCESS':
                                obj.status = 'Refund'
                                obj.save()
                                new_request = False
                                LOGGER.info('Pending refund success %s', req.ref_id)
                            elif status_data['STATUS'] == 'TXN_FAILURE':
                                LOGGER.info('Pending refund failed %s. Refund request will be initiated again.', req.ref_id)
                                new_request = True
                        else:
                            new_request = False
                    else:
                        new_request = False

                if new_request:
                    REFUND_ID = 'RF' + paytm_obj.id_generator(6)
                    refund_amount = self.amount_calc(refund_obj, thirdparty_obj)
                    LOGGER.info('Calculated Refund amount %s', refund_amount)
                    if refund_amount > 0:
                        self.stdout.write('Initiate refund amount' + str(refund_amount))
                        # paytm_obj = PayTMAPIs()
                        LOGGER.info('Sending new refund request.')
                        st, data = paytm_obj.refund_subscription(order_id=refund_obj.ref_id,
                                                                 refund_amount=refund_amount,
                                                                 trans_id=str(refund_obj.trans_id),
                                                                 refund_id=REFUND_ID,
                                                                 comments='')
                        LOGGER.info('New refund response %s, %s', st, json.dumps(data))
                        log_obj = paytm_obj.log_refund_request(ref_id=REFUND_ID,
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
                                    obj.status = 'Refund'
                                    obj.save()
                                    LOGGER.info('New refund request completed sucessfully: %s', REFUND_ID)
                                else:
                                    LOGGER.info('New refund request completed with status: %s  %s', REFUND_ID, data['STATUS'])
                            else:
                                log_obj.resp_msg = json.dumps(data)
                                log_obj.save()
                                LOGGER.info('New refund request unsuccessful: %s', REFUND_ID)
            LOGGER.info('================================================')


    def amount_calc(self, trans_obj, thirdparty_obj):
        """

        :param trans_obj:
        :param thirdparty_obj:
        :return: Amount calculation logic for cancelled paytm transactions
        """
        refund_amount = 0
        package_name = thirdparty_obj.package_id
        if thirdparty_obj.validity_start_date > thirdparty_obj.cancellation_date:
            refund_amount = trans_obj.trans_amount
        elif thirdparty_obj.validity_end_date >= thirdparty_obj.cancellation_date:
            time_diff = thirdparty_obj.validity_start_date - thirdparty_obj.cancellation_date
            no_days = time_diff.days
            if package_name == 'Quarterly':
                if no_days <= 30:
                    refund_amount = trans_obj.trans_amount - self.retained_amount
                elif no_days <= 60:
                    refund_amount = trans_obj.trans_amount - self.retained_amount * 2
            elif package_name == 'Annual':
                if no_days <= 30:
                    refund_amount = trans_obj.trans_amount - self.retained_amount
                elif no_days <= 60:
                    refund_amount = trans_obj.trans_amount - self.retained_amount * 2
                elif no_days <= 90:
                    refund_amount = trans_obj.trans_amount - self.retained_amount * 3
                elif no_days <= 120:
                    refund_amount = trans_obj.trans_amount - self.retained_amount * 4
                elif no_days <= 150:
                    refund_amount = trans_obj.trans_amount - self.retained_amount * 5
                elif no_days <= 180:
                    refund_amount = trans_obj.trans_amount - self.retained_amount * 6
        return refund_amount
