from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.hashers import make_password
from users.models import *
from meilisearch_helpers import (
    add_or_update_bank_property_in_meilisearch, 
    remove_bank_property_from_meilisearch,
    add_or_update_property_in_meilisearch,
    remove_property_from_meilisearch,
    add_or_update_wanted_property_in_meilisearch,
    remove_wanted_property_from_meilisearch
)



class CleanFloatField(models.FloatField):
    def from_db_value(self, value, expression, connection):
        return self._clean(value)

    def to_python(self, value):
        value = super().to_python(value)
        return self._clean(value)

    def _clean(self, value):
        if value is None:
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

class Property_Cat(models.Model):
    category_types = [
        ('sell', 'sell'),
        ('rent/lease', 'Rent/Lease')             
    ]
    category_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey('users.User', on_delete=models.CASCADE) #PROTECT
    category = models.CharField(max_length=100)
    category_type = models.CharField(max_length=50, choices=category_types)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now = True)

    def __str__(self):
        return f"{self.category_id}"
    

class Property(models.Model):    
    property_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='user_properties') #PROTECT
    mobile_no = models.CharField(max_length=15, null=True, blank=True, default=None)
    category_id = models.ForeignKey('Property_Cat', on_delete=models.CASCADE, null=True, blank=True,) #PROTECT  
    type = models.CharField(max_length=50, null=True, blank=True, db_index=True)  #sell or rent or lease
    admin_mobile = models.CharField(max_length=50, null=True, blank=True) 
    Admin_status = models.CharField(max_length=200, null=True, blank=True, default=None, db_index=True)
    property_name = models.CharField(max_length=50, null=True, blank=True, default=None)

    property_type = models.CharField(max_length=50, null=True, blank=True, db_index=True)       

    min_budget = CleanFloatField(null=True, blank=True)     #float   
    max_budget = CleanFloatField(null=True, blank=True)     #float   

    min_acres = CleanFloatField(null=True, blank=True)     #float   
    max_acres = CleanFloatField(null=True, blank=True)     #float   
    ratio = models.CharField(max_length=50, null=True, blank=True)
    floor = models.IntegerField(null=True, blank=True)
    
    comment = models.TextField(null=True, blank=True)

    facing =  models.CharField(max_length=50, null=True, blank=True)
    roadwidth = CleanFloatField(null=True, blank=True)     #float   
    site_area = CleanFloatField(null=True, blank=True)     #float   
    length = CleanFloatField(null=True, blank=True)     #float   
    width = CleanFloatField(null=True, blank=True)     #float   
    units = models.CharField(max_length=100, null=True, blank=True)
    buildup_area = CleanFloatField(null=True, blank=True)     #float   
    posted_by = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    price = CleanFloatField(null=True, blank=True, db_index=True)     #float with index   
    location = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    lat = models.CharField(max_length=200, null=True, blank=True, default=None, db_index=True)
    long = models.CharField(max_length=200, null=True, blank=True, default=None, db_index=True)
    nearby = models.CharField(max_length=100, null=True, blank=True)    
    no_of_flores = models.IntegerField(null=True, blank=True, db_index=True)
    _1bhk_count = models.IntegerField(null=True, blank=True, db_index=True)
    _2bhk_count = models.IntegerField(null=True, blank=True, db_index=True)
    _3bhk_count = models.IntegerField(null=True, blank=True, db_index=True)
    _4bhk_count = models.IntegerField(null=True, blank=True, db_index=True)
    rooms_count = models.IntegerField(null=True, blank=True)
    duplex_bedrooms = models.IntegerField(null=True, blank=True)
    bedrooms_count = models.IntegerField(null=True, blank=True)
    bathrooms_count = models.IntegerField(null=True, blank=True)
    shop_count = models.IntegerField(null=True, blank=True)
    house_count = models.IntegerField(null=True, blank=True)
    balcony = models.CharField(max_length=200, null=True, blank=True)
    power_backup = models.CharField(max_length=200, null=True, blank=True)
    gated_security =  models.CharField(max_length=200, null=True, blank=True)
    borewell = models.CharField(max_length=200, null=True, blank=True)
    parking = models.CharField(max_length=200, null=True, blank=True)
    lift = models.CharField(max_length=200, null=True, blank=True)    
    advance_payment = CleanFloatField(null=True, blank=True)     #float   
    boost_date = models.DateTimeField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    status  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now = True)


    def __str__(self):
        return f"{self.property_id}"

    class Meta:
        indexes = [
            models.Index(fields=['lat', 'long']),
            models.Index(fields=['type', 'Admin_status']),
            models.Index(fields=['type', 'property_type']),
            models.Index(fields=['type', 'posted_by']),
            models.Index(fields=['property_type', 'posted_by']),
            models.Index(fields=['type', 'property_type', 'Admin_status']),
        ]


# @receiver(post_save, sender=Property)
# def sync_property_to_meilisearch(sender, instance, **kwargs):
#     add_or_update_property_in_meilisearch(instance)


# @receiver(post_delete, sender=Property)
# def delete_property_from_meilisearch(sender, instance, **kwargs):
#     remove_property_from_meilisearch(instance.property_id)
    
    
class Property_images(models.Model):    
    property = models.ForeignKey('Property', on_delete=models.CASCADE, related_name='property_images') #PROTECT
    image = models.ImageField(upload_to='media/property_images/')    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for Property ID {self.property.property_id}"



class PropertyRequest(models.Model):
    req_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='user_prop_req') #PROTECT

    Looking_For_Choices = [
        ('purchase', 'purchase'),
        ('rent', 'rent'),
        ('lease', 'lease'),
        ('jv/jd', 'jv/jd'),
        ('build to suit', 'build to suit')
    ]
    looking_for = models.CharField(max_length=50, null=True, blank=True, choices=Looking_For_Choices, db_index=True)
    
    
    property_type = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    
    length = CleanFloatField(null=True, blank=True)     #float   
    width = CleanFloatField(null=True, blank=True)     #float   
    units = models.CharField(max_length=50, null=True, blank=True)
    area = CleanFloatField(null=True, blank=True)     #float   

    min_budget = CleanFloatField(null=True, blank=True)          #float      
    max_budget = CleanFloatField(null=True, blank=True)     #float   

    no_of_bedrooms = models.IntegerField(null=True, blank=True)
    min_monthly_rent = CleanFloatField(null=True, blank=True)      #float   
    max_monthly_rent = CleanFloatField(null=True, blank=True)       #float     
    
    min_year_lease = CleanFloatField(null=True, blank=True)     #float   
    max_year_lease = CleanFloatField(null=True, blank=True)     #float   

    min_acres = CleanFloatField(null=True, blank=True)     #float   
    max_acres = CleanFloatField(null=True, blank=True)     #float   

    min_budget_per_acre = CleanFloatField(null=True, blank=True)     #float   
    max_budget_per_acre = CleanFloatField(null=True, blank=True)     #float   
    min_expected_rental_income = CleanFloatField(null=True, blank=True)     #float   
    max_expected_rental_income = CleanFloatField(null=True, blank=True)     #float   
    
    ratio = models.CharField(max_length=50, null=True, blank=True)
    floor = models.IntegerField(null=True, blank=True)
    
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now = True)
    
    def __str__(self):
        return f"{self.req_id}"


@receiver(post_save, sender=PropertyRequest)
def sync_property_request_to_meilisearch(sender, instance, **kwargs):
    add_or_update_wanted_property_in_meilisearch(instance)


@receiver(post_delete, sender=PropertyRequest)
def delete_property_request_from_meilisearch(sender, instance, **kwargs):
    remove_wanted_property_from_meilisearch(instance.req_id)


class PropertyRequestLocations(models.Model):
    loc_id = models.AutoField(primary_key=True)
    req_id = models.ForeignKey('PropertyRequest', on_delete=models.CASCADE, related_name='pro_loc') #PROTECT 
    location = models.CharField(max_length=200, null=True, blank=True)
    lat = models.CharField(max_length=200, null=True, blank=True, default=None)
    long = models.CharField(max_length=200, null=True, blank=True, default=None)

    def __str__(self):
        return f"{self.loc_id}"
    
    
class ResponsePropertyRequest(models.Model):
    resp_id = models.AutoField(primary_key=True)
    req_id = models.ForeignKey('PropertyRequest', on_delete=models.CASCADE, related_name='user_req') #PROTECT 
    user_id = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='user_prop_res') #PROTECT

    comment = models.TextField(null=True, blank=True)
    proerty_link = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now = True)
    
    def __str__(self):
        return f"{self.resp_id}"
    



class BankAuctionProperty(models.Model):

    Status = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    bankprop_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='user_bank_prop', blank=True, null=True) #PROTECT
    
    auction_id = models.CharField(max_length=50, unique=True, blank=True, null=True)    
    bank_name = models.CharField(max_length=200, blank=True, null=True)
    property_type = models.CharField(max_length=200, blank=True, null=True)
    action_type = models.CharField(max_length=100, blank=True, null=True)

    location = models.CharField(max_length=255, blank=True, null=True)
    city_town = models.CharField(max_length=100, blank=True, null=True)
    area_town = models.CharField(max_length=100, blank=True, null=True)
    lat = models.CharField(max_length=200, null=True, blank=True, default=None)
    long = models.CharField(max_length=200, null=True, blank=True, default=None)

    area = CleanFloatField(blank=True, null=True)  # 900 sft     #float   
    units = models.CharField(max_length=100, blank=True, null=True)
    possession = models.CharField(max_length=100, blank=True, null=True)
    reserve_price = models.CharField(max_length=100, blank=True, null=True)
    possession_status = models.CharField(max_length=100, blank=True, null=True)
    emd_amount = CleanFloatField(blank=True, null=True)     #float   

    bid_increment = CleanFloatField(blank=True, null=True)     #float   

    emd_submission = models.DateTimeField(blank=True, null=True)
    auction_start_datetime = models.DateTimeField(blank=True, null=True)
    auction_end_datetime = models.DateTimeField(blank=True, null=True)

    bank_contact_details = models.CharField(max_length=200, blank=True, null=True)    

    description = models.TextField(blank=True, null=True)
    admin_status = models.CharField(choices=Status, max_length=100, default='Pending', null=True, blank=True)
    status= models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)   # auto refresh on update

    def __str__(self):
        return f"{self.bank_name} - {self.auction_id}"


# @receiver(post_save, sender=BankAuctionProperty)
# def sync_bank_property_to_meilisearch(sender, instance, **kwargs):
#     add_or_update_bank_property_in_meilisearch(instance)


# @receiver(post_delete, sender=BankAuctionProperty)
# def delete_bank_property_from_meilisearch(sender, instance, **kwargs):
#     remove_bank_property_from_meilisearch(instance.bankprop_id)


class BankAuctionPropertyDocs(models.Model):
    doc_id = models.AutoField(primary_key=True)
    bankpro_id = models.ForeignKey('BankAuctionProperty', on_delete=models.CASCADE, related_name='bank_pro_doc') #PROTECT 
    document = models.FileField(upload_to='media/bank_property_docs/')    
    uploaded_at = models.DateTimeField(auto_now_add=True)   

    def __str__(self):
        return f"{self.doc_id}"
    





# class AdProperty(models.Model):    
#     property_id = models.AutoField(primary_key=True)
#     user_id = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='user_adproperties') #PROTECT
#     mobile_no = models.CharField(max_length=15, null=True, blank=True, default=None)
#     category_id = models.ForeignKey('Property_Cat', on_delete=models.CASCADE, null=True, blank=True,) #PROTECT  
#     type = models.CharField(max_length=50, null=True, blank=True, db_index=True)  #sell or rent or lease
#     admin_mobile = models.CharField(max_length=50, null=True, blank=True) 
#     Admin_status = models.CharField(max_length=200, null=True, blank=True, default=None, db_index=True)
#     property_name = models.CharField(max_length=50, null=True, blank=True, default=None)

#     property_type = models.CharField(max_length=50, null=True, blank=True, db_index=True)       

#     min_budget = CleanFloatField(null=True, blank=True)     #float   
#     max_budget = CleanFloatField(null=True, blank=True)     #float   

#     min_acres = CleanFloatField(null=True, blank=True)     #float   
#     max_acres = CleanFloatField(null=True, blank=True)     #float   
#     ratio = models.CharField(max_length=50, null=True, blank=True)
#     floor = models.IntegerField(null=True, blank=True)
    
#     comment = models.TextField(null=True, blank=True)

#     facing =  models.CharField(max_length=50, null=True, blank=True)
#     roadwidth = CleanFloatField(null=True, blank=True)     #float   
#     site_area = CleanFloatField(null=True, blank=True)     #float   
#     length = CleanFloatField(null=True, blank=True)     #float   
#     width = CleanFloatField(null=True, blank=True)     #float   
#     units = models.CharField(max_length=100, null=True, blank=True)
#     buildup_area = CleanFloatField(null=True, blank=True)     #float   
#     posted_by = models.CharField(max_length=50, null=True, blank=True, db_index=True)
#     price = CleanFloatField(null=True, blank=True, db_index=True)     #float with index   
#     location = models.CharField(max_length=200, null=True, blank=True, db_index=True)
#     lat = models.CharField(max_length=200, null=True, blank=True, default=None, db_index=True)
#     long = models.CharField(max_length=200, null=True, blank=True, default=None, db_index=True)
#     nearby = models.CharField(max_length=100, null=True, blank=True)    
#     no_of_flores = models.IntegerField(null=True, blank=True, db_index=True)
#     _1bhk_count = models.IntegerField(null=True, blank=True, db_index=True)
#     _2bhk_count = models.IntegerField(null=True, blank=True, db_index=True)
#     _3bhk_count = models.IntegerField(null=True, blank=True, db_index=True)
#     _4bhk_count = models.IntegerField(null=True, blank=True, db_index=True)
#     rooms_count = models.IntegerField(null=True, blank=True)
#     duplex_bedrooms = models.IntegerField(null=True, blank=True)
#     bedrooms_count = models.IntegerField(null=True, blank=True)
#     bathrooms_count = models.IntegerField(null=True, blank=True)
#     shop_count = models.IntegerField(null=True, blank=True)
#     house_count = models.IntegerField(null=True, blank=True)
#     balcony = models.CharField(max_length=200, null=True, blank=True)
#     power_backup = models.CharField(max_length=200, null=True, blank=True)
#     gated_security =  models.CharField(max_length=200, null=True, blank=True)
#     borewell = models.CharField(max_length=200, null=True, blank=True)
#     parking = models.CharField(max_length=200, null=True, blank=True)
#     lift = models.CharField(max_length=200, null=True, blank=True)    
#     advance_payment = CleanFloatField(null=True, blank=True)     #float   
#     boost_date = models.DateTimeField(null=True, blank=True)
#     description = models.TextField(null=True, blank=True)
#     status  = models.BooleanField(default=True)
#     adstart_date = models.DateTimeField(null=True, blank=True)
#     adend_date = models.DateTimeField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now = True)


#     def __str__(self):
#         return f"{self.property_id}"

#     class Meta:
#         indexes = [
#             models.Index(fields=['lat', 'long']),
#             models.Index(fields=['type', 'Admin_status']),
#             models.Index(fields=['type', 'property_type']),
#             models.Index(fields=['type', 'posted_by']),
#             models.Index(fields=['property_type', 'posted_by']),
#             models.Index(fields=['type', 'property_type', 'Admin_status']),
#         ]


# class AdProperty_images(models.Model):    
#     property = models.ForeignKey('AdProperty', on_delete=models.CASCADE, related_name='AdProperty_images') #PROTECT
#     image = models.ImageField(upload_to='media/AdProperty_images/')    
#     uploaded_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Image for Property ID {self.property.property_id}"



from django.db import models
from django.core.validators import MinValueValidator


# ============================================================
# MAIN PROPERTY / PROJECT
# ============================================================

class AdProperty(models.Model):

    property_id = models.AutoField(
        primary_key=True
    )

    # ========================================================
    # USER / CATEGORY
    # ========================================================

    user_id = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='user_adproperties'
    )

    category_id = models.ForeignKey(
        'Property_Cat',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ad_properties'
    )

    mobile_no = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        default=None
    )

    admin_mobile = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    Admin_status = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        default=None,
        db_index=True
    )

    # ========================================================
    # PROJECT DETAILS
    # ========================================================

    property_name = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        default=None
    )

    property_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True
    )

    # Sell / Rent / Lease
    type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True
    )

    address = models.TextField(
        null=True,
        blank=True
    )

    city = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True
    )

    location = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        db_index=True
    )

    landmark = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    lat = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        default=None,
        db_index=True
    )

    long = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        default=None,
        db_index=True
    )

    possession_date = models.DateField(
        null=True,
        blank=True
    )

    # ========================================================
    # PROJECT DESCRIPTION
    # ========================================================

    description = models.TextField(
        null=True,
        blank=True,
        max_length=2000
    )

    # Comma-separated
    tags = models.TextField(
        null=True,
        blank=True
    )

    # ========================================================
    # BUDGET
    # ========================================================

    min_budget = models.FloatField(
        null=True,
        blank=True
    )

    max_budget = models.FloatField(
        null=True,
        blank=True
    )

    # ========================================================
    # LAND / AREA
    # ========================================================

    min_acres = models.FloatField(
        null=True,
        blank=True
    )

    max_acres = models.FloatField(
        null=True,
        blank=True
    )

    ratio = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    floor = models.IntegerField(
        null=True,
        blank=True
    )

    roadwidth = models.FloatField(
        null=True,
        blank=True
    )

    site_area = models.FloatField(
        null=True,
        blank=True
    )

    length = models.FloatField(
        null=True,
        blank=True
    )

    width = models.FloatField(
        null=True,
        blank=True
    )

    units = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    buildup_area = models.FloatField(
        null=True,
        blank=True
    )

    # ========================================================
    # GENERAL PROPERTY INFORMATION
    # ========================================================

    posted_by = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True
    )

    price = models.FloatField(
        null=True,
        blank=True,
        db_index=True
    )

    nearby = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    no_of_floors = models.IntegerField(
        null=True,
        blank=True,
        db_index=True
    )

    rooms_count = models.IntegerField(
        null=True,
        blank=True
    )

    duplex_bedrooms = models.IntegerField(
        null=True,
        blank=True
    )

    bedrooms_count = models.IntegerField(
        null=True,
        blank=True
    )

    bathrooms_count = models.IntegerField(
        null=True,
        blank=True
    )

    shop_count = models.IntegerField(
        null=True,
        blank=True
    )

    house_count = models.IntegerField(
        null=True,
        blank=True
    )

    # ========================================================
    # LEGACY / GENERAL FEATURES
    # ========================================================

    facing = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    balcony = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    power_backup = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    gated_security = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    borewell = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    parking = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    lift = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    advance_payment = models.FloatField(
        null=True,
        blank=True
    )

    # ========================================================
    # STATUS / DATES
    # ========================================================

    status = models.BooleanField(
        default=True
    )

    adstart_date = models.DateTimeField(
        null=True,
        blank=True
    )

    adend_date = models.DateTimeField(
        null=True,
        blank=True
    )

    boost_date = models.DateTimeField(
        null=True,
        blank=True
    )
    
    displaying_pannels = models.JSONField(
        default=list,
        blank=True,
        null=True
    )

    radius_distance = models.CharField(max_length=100, null=True, blank=True)
    radius_distance_units = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.property_id} - {self.property_name}"

    class Meta:
        indexes = [
            models.Index(
                fields=['lat', 'long']
            ),
            models.Index(
                fields=['type', 'Admin_status']
            ),
            models.Index(
                fields=['type', 'property_type']
            ),
            models.Index(
                fields=['type', 'posted_by']
            ),
            models.Index(
                fields=['property_type', 'posted_by']
            ),
            models.Index(
                fields=[
                    'type',
                    'property_type',
                    'Admin_status'
                ]
            ),
            models.Index(
                fields=[
                    'city',
                    'property_type'
                ]
            ),
        ]


# ============================================================
# HERO IMAGES
# Maximum 5 images should be enforced in serializer
# ============================================================

class AdProperty_images(models.Model):
       
    property = models.ForeignKey(AdProperty, on_delete=models.CASCADE, related_name='hero_images')
    image = models.ImageField(upload_to='media/AdProperty_hero_images/')
    order = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(1)
        ]
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['order']

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'property',
                    'order'
                ],
                name='unique_property_hero_image_order'
            )
        ]

    def __str__(self):
        return (
            f"Hero Image - "
            f"Property {self.property.property_id}"
        )


# ============================================================
# BUILDER DETAILS
# One builder record per property
# ============================================================

class AdPropertyBuilderDetails(models.Model):

    property = models.OneToOneField(
        AdProperty,
        on_delete=models.CASCADE,
        related_name='builder_details'
    )

    builder_name = models.CharField(
        max_length=200
    )

    city = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    projects_completed = models.PositiveIntegerField(
        default=0
    )

    ongoing_projects = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.builder_name


# ============================================================
# PROPERTY CONFIGURATIONS
# 1BHK / 2BHK / 3BHK / 4BHK / 4+BHK
# ============================================================

class AdPropertyConfiguration(models.Model):

    BHK_CHOICES = [
        ('1BHK', '1 BHK'),
        ('2BHK', '2 BHK'),
        ('3BHK', '3 BHK'),
        ('4BHK', '4 BHK'),
        ('4+BHK', '4+ BHK'),
    ]

    property = models.ForeignKey(
        AdProperty,
        on_delete=models.CASCADE,
        related_name='configurations'
    )

    bhk_type = models.CharField(
        max_length=20,
        choices=BHK_CHOICES
    )

    # ========================================================
    # AREA
    # ========================================================

    carpet_area = models.FloatField(
        null=True,
        blank=True
    )

    built_up_area = models.FloatField(
        null=True,
        blank=True
    )

    super_built_up_area = models.FloatField(
        null=True,
        blank=True
    )

    # ========================================================
    # PRICE
    # ========================================================

    price = models.FloatField(
        null=True,
        blank=True
    )

    # ========================================================
    # DETAILS
    # ========================================================

    facing = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    bathrooms = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    balcony = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    parking = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['bhk_type']

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'property',
                    'bhk_type'
                ],
                name='unique_property_bhk_configuration'
            )
        ]

    def __str__(self):
        return (
            f"{self.property.property_name} - "
            f"{self.bhk_type}"
        )


# ============================================================
# 2D / 3D FLOOR PLAN IMAGES
# One 2D + one 3D image per configuration
# ============================================================

class AdPropertyFloorPlanImage(models.Model):

    PLAN_TYPE_CHOICES = [
        ('2D', '2D'),
        ('3D', '3D'),
    ]

    configuration = models.ForeignKey(
        AdPropertyConfiguration,
        on_delete=models.CASCADE,
        related_name='floor_plan_images'
    )

    plan_type = models.CharField(
        max_length=10,
        choices=PLAN_TYPE_CHOICES
    )

    image = models.ImageField(
        upload_to='media/AdProperty_floor_plans/'
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'configuration',
                    'plan_type'
                ],
                name='unique_configuration_plan_type'
            )
        ]

    def __str__(self):
        return (
            f"{self.configuration} - "
            f"{self.plan_type}"
        )


# ============================================================
# LOCATION ADVANTAGES
# Maximum 8 per property
# ============================================================

class AdPropertyLocationAdvantage(models.Model):

    property = models.ForeignKey(
        AdProperty,
        on_delete=models.CASCADE,
        related_name='location_advantages'
    )

    place_name = models.CharField(
        max_length=200
    )

    distance = models.CharField(
        max_length=100,
        help_text="Example: 2.5 km"
    )

    travel_time = models.CharField(
        max_length=100,
        help_text="Example: 10 min"
    )

    order = models.PositiveSmallIntegerField(
        default=1
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['order']

        constraints = [
            models.UniqueConstraint(
                fields=[
                    'property',
                    'order'
                ],
                name='unique_property_location_order'
            )
        ]

    def __str__(self):
        return (
            f"{self.place_name} - "
            f"{self.property.property_name}"
        )


# ============================================================
# PROPERTY HIGHLIGHTS
# Single model as requested
# ============================================================

class AdPropertyHighlight(models.Model):

    property = models.ForeignKey(
        AdProperty,
        on_delete=models.CASCADE,
        related_name='property_highlights'
    )

    name = models.CharField(
        max_length=100
    )

    icon = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    order = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return (
            f"{self.property.property_name} - "
            f"{self.name}"
        )


# ============================================================
# PROPERTY AMENITIES
# Single model as requested
# ============================================================

class AdPropertyAmenity(models.Model):

    property = models.ForeignKey(
        AdProperty,
        on_delete=models.CASCADE,
        related_name='property_amenities'
    )

    name = models.CharField(
        max_length=100
    )

    icon = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    order = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return (
            f"{self.property.property_name} - "
            f"{self.name}"
        )


# ============================================================
# PROPERTY SPECIFICATIONS
# Dynamic key/value pairs
# ============================================================

class AdPropertySpecification(models.Model):

    property = models.ForeignKey(
        AdProperty,
        on_delete=models.CASCADE,
        related_name='specifications'
    )

    name = models.CharField(
        max_length=150
    )

    value = models.TextField(
        max_length=1000
    )

    order = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return (
            f"{self.property.property_name} - "
            f"{self.name}"
        )


# ============================================================
# BROCHURES
# ============================================================

class AdPropertyBrochure(models.Model):

    property = models.ForeignKey(
        AdProperty,
        on_delete=models.CASCADE,
        related_name='brochures'
    )

    title = models.CharField(
        max_length=200
    )

    document = models.FileField(
        upload_to='media/AdProperty_brochures/'
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.title} - "
            f"{self.property.property_name}"
        )







