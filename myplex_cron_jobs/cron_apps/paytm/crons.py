from django_cron import CronJobBase, Schedule
from cron_apps.paytm.paytm_crons_utils import PaytmCronsUtils

class PaytmRefundCron(CronJobBase):
    """
        PAYTM refund cron
    """
    RUN_EVERY_MINS = 5  # every 5 Mins

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'cron_apps.paytm.refund_cron'    # a unique code

    def do(self):
        PaytmCronsUtils().refund_script()