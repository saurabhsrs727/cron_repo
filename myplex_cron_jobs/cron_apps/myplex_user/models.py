# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from cron_apps.myplex_user import constants
# Create your models here.
import hashlib
import logging



LOGGER = logging.getLogger("myplex_service.cron_apps.myplex_user.models")

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
    ('N', 'Not Specified'),
)


class User(models.Model):
    """
        User Model
    """
    first = models.CharField(max_length=64, blank=True, db_index=True)
    last = models.CharField(max_length=64, blank=True, db_index=True)
    password_hash = models.CharField(max_length=128, null=True)  # password hash is sha256 hash digest of user password plus salt
    mobile_no = models.CharField(max_length=32, null=True)
    mobile_no_verified = models.BooleanField(default=False)
    email_id = models.EmailField(max_length=75, null=True)
    dob = models.DateField(null=True)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, default='N')
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    guest_device = models.OneToOneField("Device",
                                        db_index=True,
                                        null=True,
                                        default=None,
                                        related_name='guest_user')  # associated device if this is guest account
    free_subscriber = models.IntegerField(default=0)  # Flag to decide if free user
    age = models.CharField(max_length=20, blank=True, db_index=True)

    @staticmethod
    def make_password(raw_password):
        return hashlib.sha256(raw_password + constants.PASSWORD_SALT).hexdigest()

    def set_password(self, raw_password):
        self.password_hash = self.make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        return self.password_hash == self.make_password(raw_password)

    def full_name(self):
        return ' '.join([self.first, self.last])

    def is_guest(self):
        return self.guest_device is not None

    @property
    def subProfile(self):
        # Will return sub profile object or None
        return self.child_set.all().first()

    def display_name(self):
        name = self.full_name().strip()
        if name:
            return name
        # return email address without domain
        try:
            user_email = self.useremail_set.all()[0]
            tokens = user_email.email.split('@')
            return tokens[0] if tokens else ''
        except:
            return ""

    def __unicode__(self):
        fields = [self.id, self.first, self.last]
        return " ".join([unicode(f) for f in fields if f])


class Device(models.Model):
    """
        Device model for storing devices
    """
    os = models.CharField(max_length=64, db_index=True)
    os_version = models.CharField(max_length=64)
    make = models.CharField(max_length=64, db_index=True)
    model = models.CharField(max_length=128)
    resolution = models.CharField(max_length=12)  # resolution in widthxheight e.g. 800x1200
    serial_number = models.CharField(max_length=255, db_index=True)  # device serial number, can be something unique e.g. Mac id.
    profile = models.CharField(max_length=32)  # profile, allows more than one device ids to be associated with a device
    device_id = models.CharField(unique=True, db_index=True, max_length=128)
    service_id = models.CharField(max_length=255, db_index=True, default='myplex')
    user = models.ForeignKey(User, null=True, blank=True, default=None)
    mso_subscriber_id = models.CharField(max_length=12, default='NA')
    status = models.CharField(max_length=32, default='NA')
    friendly_name = models.CharField(max_length=64, default='home')
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('os', 'make', 'model', 'serial_number', 'profile'), ]

    def __unicode__(self):
        return self.os + self.os_version + self.serial_number + self.profile

    def user_email(self):
        if not self.user:
            return ''
        return self.user.useremail_set.all()[0].email


class ThirdpartySubscriber(models.Model):
    """
        ThirdPartySubscriber model for subscription
    """
    mobile = models.CharField(max_length=32, null=True)
    email = models.EmailField(max_length=75, null=True)
    user_id = models.IntegerField(null=True)
    first_name = models.CharField(max_length=64, null=True)
    last_name = models.CharField(max_length=64, null=True)
    country_code = models.CharField(max_length=2, null=True)
    package_id = models.CharField(max_length=20, null=True)
    partner_id = models.IntegerField()
    partner_name = models.CharField(max_length=20)
    user_activated = models.IntegerField(default=0)  # tinyint(4) in db
    user_activation_mode = models.CharField(max_length=10)
    validity_start_date = models.DateTimeField()
    validity_end_date = models.DateTimeField()
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)
    cancellation_date = models.DateTimeField(null=True)
    Partner_User_id = models.CharField(max_length=32, null=True)

    class Meta:
        db_table = 'myplex_thirdparty_subscriber'
