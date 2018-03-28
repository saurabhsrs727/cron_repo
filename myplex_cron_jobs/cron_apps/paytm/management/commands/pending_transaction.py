from django.core.management.base import BaseCommand
from apps.paytm.models import *
from apps.paytm.paytm_utils import PayTMAPIs

class Command(BaseCommand):
    help = 'Commands for pending paytm transaction'

    def handle(self, *args, **options):
        txn_objs = PayTMTransaction.objects.filter(status='PENDING')
        paytm_obj = PayTMAPIs()
        for obj in txn_objs:
            if obj.request_type == 'REFUND':
                refund_status, status_data = paytm_obj.refund_status_response(obj.refund_order_id, obj.ref_id)
                if refund_status == 200:
                    status_data = status_data['REFUND_LIST'][0]
                    paytm_obj.update_refund_log(ref_id=obj.ref_id,
                                                status=status_data['STATUS'],
                                                resp_msg=status_data['RESPMSG'],
                                                gateway_name=status_data['GATEWAY'],
                                                payment_mode=status_data['PAYMENTMODE'],
                                                bank_trans_id=status_data['BANKTXNID'],
                                                trans_date=status_data['TXNDATE'],
                                                trans_id=status_data['TXNID'],
                                                refund_date=status_data['REFUNDDATE'])
                    self.stdout.write('Refund request log updated.')
            else:
                req_st, status_data = paytm_obj.trans_status_response(obj.ref_id)
                if req_st == 200:
                    paytm_obj.update_subscribe_log(ref_id=status_data['ORDERID'],
                                                   status=status_data['STATUS'],
                                                   resp_msg=status_data['RESPMSG'],
                                                   gateway_name=status_data['GATEWAYNAME'],
                                                   payment_mode=status_data['PAYMENTMODE'],
                                                   bank_name=status_data['BANKNAME'],
                                                   bank_trans_id=status_data['BANKTXNID'],
                                                   trans_date=status_data['TXNDATE'],
                                                   trans_id=status_data['TXNID'],
                                                   subscription_id=status_data['SUBS_ID'],
                                                   trans_type=status_data['TXNTYPE'],
                                                   refund_amount=status_data['REFUNDAMT'])
                    self.stdout.write('subscribe request log updated.')