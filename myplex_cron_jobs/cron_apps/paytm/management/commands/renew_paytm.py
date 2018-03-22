from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from apps.paytm.models import *
from apps.paytm.paytm_utils import PayTMAPIs
import requests
import datetime

class Command(BaseCommand):
    help = 'Commands for renewal paytm transaction'
    retained_amount = 50

    def handle(self, *args, **options):
        today = timezone.now()
        paytm_subs_status = PayTMSubscriptionStatus.objects.filter(status='Subscribe',
                                                            thirdparty_subscriber__validity_end_date__lt=today,
                                                            thirdparty_subscriber__user_activated=1)


        for obj in paytm_subs_status:
            log_obj = PayTMTransaction.objects.filter(status='TXN_SUCCESS', ref_id=obj.order_id).first()
            if log_obj:
                self.stdout.write('Renewal started')
                paytm_obj = PayTMAPIs()
                renewal_url = paytm_obj.subs_renew_trans_req_url(trans_amount=log_obj.trans_amount,
                                                                 order_id=log_obj.ref_id)
                renewal_resp = requests.get(renewal_url).json()

                paytm_obj.update_subscribe_log(ref_id=renewal_resp['ORDERID'],
                                               status=renewal_resp['STATUS'],
                                               resp_msg=renewal_resp['RESPMSG'],
                                               gateway_name=renewal_resp['GATEWAYNAME'],
                                               payment_mode=renewal_resp['PAYMENTMODE'],
                                               bank_name=renewal_resp['BANKNAME'],
                                               bank_trans_id=renewal_resp['BANKTXNID'],
                                               trans_date=renewal_resp['TXNDATE'],
                                               trans_id=renewal_resp['TXNID'],
                                               subscription_id=renewal_resp['SUBS_ID'],
                                               trans_type=renewal_resp['TXNTYPE'],
                                               refund_amount=renewal_resp['REFUNDAMT'])

                if renewal_resp['STATUS'] == 'TXN_SUCCESS':
                    validity_start_date = log_obj.subs_start_date
                    if log_obj.package_name == 'Monthly':
                        validity_end_date = validity_start_date + datetime.timedelta(days=30)
                    elif log_obj.package_name == 'Quarterly':
                        validity_end_date = validity_start_date + datetime.timedelta(days=90)
                    elif log_obj.package_name == 'Annual':
                        validity_end_date = validity_start_date + datetime.timedelta(days=365)

                    third_party_obj = paytm_obj.insert_third_party(user_id=log_obj.user_id,
                                                                   start_date=validity_start_date,
                                                                   end_date=validity_end_date,
                                                                   package_id=log_obj.subs_service_id)
                    paytm_obj.insert_third_party_renewal(user_id=log_obj.user_id,
                                                         start_date=validity_start_date,
                                                         end_date=validity_end_date)
                    paytm_obj.insert_paytm_subs_status(user_id=log_obj.user,
                                                       status='Subscribe',
                                                       third_party_obj=third_party_obj,
                                                       order_id=renewal_resp['ORDERID'],
                                                       plan_to_switch=log_obj.package_name)


