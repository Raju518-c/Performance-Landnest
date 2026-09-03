from rest_framework import serializers
from .models import *
from users.models import *
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.hashers import make_password


class Property_CatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property_Cat
        fields = '__all__'


class Property_imagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property_images
        fields = '__all__'


class PropertySerializer(serializers.ModelSerializer):
    property_images = Property_imagesSerializer(many=True, read_only=True)
    new_property_images = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)

    category_name = serializers.CharField(
        source='category_id.category',
        read_only=True
    )

    # User details
    user_first_name = serializers.CharField(source='user_id.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user_id.last_name', read_only=True)
    user_mobile_no = serializers.CharField(source='user_id.mobile_no', read_only=True)
    user_email = serializers.EmailField(source='user_id.email', read_only=True)

    class Meta:
        model = Property
        fields = '__all__'

    def create(self, validated_data):
        new_images = validated_data.pop('new_property_images', [])
        property_instance = Property.objects.create(**validated_data)

        for image in new_images:
            Property_images.objects.create(property=property_instance, image=image)

        return property_instance



class SellPropertyCoordinatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ('property_id', 'type', 'lat', 'long', 'category_id', 'price')


class PropertyMapSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for map properties with single image
    """
    first_image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category_id.category', read_only=True)

    class Meta:
        model = Property
        # fields = (
        #     'property_id', 'type', 'lat', 'long', 'category_id', 'category_name', 
        #     'price', 'property_name', 'location', 'first_image'
        # )
        fields = '__all__'

    def get_first_image(self, obj):
        """
        Get only the first image for the property to optimize performance
        """
        first_image = obj.property_images.first()
        if first_image and first_image.image:
            return first_image.image.url
        return None




class Property_new_imagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property_images
        fields = ('image', 'uploaded_at')



class SellPropertySummarySerializer(serializers.ModelSerializer):
    property_images = serializers.SerializerMethodField()

    category = serializers.CharField(
        source='category_id.category',
        read_only=True
    )

    class Meta:
        model = Property
        fields = (
            'property_id',
            'property_images',
            'category_id',
            'category',
            'type',
            'property_name',
            'property_type',
            'mobile_no',
            'facing',
            'site_area',
            'length',
            'width',
            'units',
            'posted_by',
            'price',
            'location',
            'lat',
            'long',
            'created_at',
        )

    def get_property_images(self, obj):
        first_image = obj.property_images.first()

        if first_image:
            # Wrap single record inside a list
            return [Property_new_imagesSerializer(first_image).data]

        return []



class boostpropertyserializer(serializers.Serializer):    
    user_id = serializers.CharField(write_only=True) 




class ResponsePropertyRequestSerializer(serializers.ModelSerializer):    
    class Meta:
        model = ResponsePropertyRequest
        fields = '__all__'



class PropertyRequestLocationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyRequestLocations
        fields = '__all__'


class NewLocationSerializer(serializers.Serializer):
    # This defines the exact fields Swagger should show for new_locations
    location = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    lat = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    long = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class PropertyRequestSerializer(serializers.ModelSerializer):
    pro_loc = PropertyRequestLocationsSerializer(many=True, read_only=True)

    # Include user information directly like BankAuctionPropertySerializer
    user_first_name = serializers.CharField(source='user_id.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user_id.last_name', read_only=True)
    user_mobile_no = serializers.CharField(source='user_id.mobile_no', read_only=True)
    user_username = serializers.CharField(source='user_id.username', read_only=True)

    # Combined locations string field
    locations_str = serializers.SerializerMethodField()

    # Use the typed nested serializer so swagger shows exact keys instead of additionalPropX
    new_locations = NewLocationSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = PropertyRequest
        fields = '__all__'

    def get_locations_str(self, obj):
        """
        Get all locations combined as a comma-separated string
        """
        locations = obj.pro_loc.all()
        location_str = ', '.join([loc.location for loc in locations if loc.location]) if locations else '-'
        return location_str

    def create(self, validated_data):
        new_locations = validated_data.pop('new_locations', [])
        req_obj = PropertyRequest.objects.create(**validated_data)

        # create location rows
        for loc in new_locations:
            # loc is a dict with keys: location, lat, long
            PropertyRequestLocations.objects.create(req_id=req_obj, **loc)

        return req_obj

    def update(self, instance, validated_data):
        new_locations = validated_data.pop('new_locations', [])

        # update main request fields
        instance = super().update(instance, validated_data)

        # add new locations
        for loc in new_locations:
            PropertyRequestLocations.objects.create(req_id=instance, **loc)

        return instance



class BankAuctionPropertyDocsSerializer(serializers.ModelSerializer):    
    class Meta:
        model = BankAuctionPropertyDocs
        fields = '__all__'


class BankAuctionPropertySerializer(serializers.ModelSerializer):

    bank_pro_doc = BankAuctionPropertyDocsSerializer(many=True, read_only=True)
    
    # Include user information
    user_first_name = serializers.CharField(source='user_id.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user_id.last_name', read_only=True)
    user_mobile_no = serializers.CharField(source='user_id.mobile_no', read_only=True)
    user_email = serializers.EmailField(source='user_id.email', read_only=True)

    # For uploading new documents
    new_documents = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)

    class Meta:
        model = BankAuctionProperty
        fields = '__all__'

    def create(self, validated_data):
        new_docs = validated_data.pop('new_documents', [])

        obj = BankAuctionProperty.objects.create(**validated_data)

        for doc in new_docs:
            BankAuctionPropertyDocs.objects.create(
                bankpro_id=obj,
                document=doc
            )

        return obj

    def update(self, instance, validated_data):
        new_docs = validated_data.pop('new_documents', [])

        instance = super().update(instance, validated_data)

        # Add new documents
        for doc in new_docs:
            BankAuctionPropertyDocs.objects.create(
                bankpro_id=instance,
                document=doc
            )

        return instance


class FilteredPropertyResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    data = serializers.ListField()
    
    
class ViewportBoundsSerializer(serializers.Serializer):
    north = serializers.FloatField(required=False)
    south = serializers.FloatField(required=False)
    east = serializers.FloatField(required=False)
    west = serializers.FloatField(required=False)


class FilteredPropertyRequestSerializer(serializers.Serializer):
    include = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        default={}
    )

    exclude = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        default={}
    )

    viewport_bounds = ViewportBoundsSerializer(
        required=False,
        allow_null=True
    )

    limit = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    for_map = serializers.BooleanField(
        required=False,
        default=False
    )




# class AdProperty_imagesSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = AdProperty_images
#         fields = "__all__"


# class AdPropertySerializer(serializers.ModelSerializer):

#     AdProperty_images = AdProperty_imagesSerializer(
#         many=True,
#         read_only=True
#     )

#     new_property_images = serializers.ListField(
#         child=serializers.ImageField(),
#         write_only=True,
#         required=False
#     )

#     category_name = serializers.CharField(
#         source="category_id.category",
#         read_only=True
#     )

#     user_first_name = serializers.CharField(
#         source="user_id.first_name",
#         read_only=True
#     )

#     user_last_name = serializers.CharField(
#         source="user_id.last_name",
#         read_only=True
#     )

#     user_mobile_no = serializers.CharField(
#         source="user_id.mobile_no",
#         read_only=True
#     )

#     user_email = serializers.EmailField(
#         source="user_id.email",
#         read_only=True
#     )

#     class Meta:
#         model = AdProperty
#         fields = "__all__"

#     def create(self, validated_data):

#         images = validated_data.pop(
#             "new_property_images",
#             []
#         )

#         property_obj = AdProperty.objects.create(
#             **validated_data
#         )

#         if images:
#             AdProperty_images.objects.bulk_create(
#                 [
#                     AdProperty_images(
#                         property=property_obj,
#                         image=image
#                     )
#                     for image in images
#                 ]
#             )

#         return property_obj

#     def update(self, instance, validated_data):

#         images = validated_data.pop(
#             "new_property_images",
#             []
#         )

#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)

#         instance.save()

#         if images:
#             AdProperty_images.objects.bulk_create(
#                 [
#                     AdProperty_images(
#                         property=instance,
#                         image=image
#                     )
#                     for image in images
#                 ]
#             )

#         return instance
    






# ============================================================
# HERO IMAGE
# ============================================================

class AdProperty_imagesSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdProperty_images
        fields = "__all__"

        read_only_fields = [
            "id",
            "uploaded_at",
        ]


# ============================================================
# BUILDER DETAILS
# ============================================================

class AdPropertyBuilderDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertyBuilderDetails
        fields = "__all__"

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


# ============================================================
# FLOOR PLAN
# ============================================================

class AdPropertyFloorPlanImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertyFloorPlanImage
        fields = "__all__"

        read_only_fields = [
            "id",
            "uploaded_at",
        ]


# ============================================================
# CONFIGURATION
# ============================================================

class AdPropertyConfigurationSerializer(serializers.ModelSerializer):

    floor_plan_images = AdPropertyFloorPlanImageSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = AdPropertyConfiguration
        fields = "__all__"

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


# ============================================================
# LOCATION ADVANTAGE
# ============================================================

class AdPropertyLocationAdvantageSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertyLocationAdvantage
        fields = "__all__"

        read_only_fields = [
            "id",
            "created_at",
        ]


# ============================================================
# HIGHLIGHT
# ============================================================

class AdPropertyHighlightSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertyHighlight
        fields = "__all__"

        read_only_fields = [
            "id",
            "created_at",
        ]


# ============================================================
# AMENITY
# ============================================================

class AdPropertyAmenitySerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertyAmenity
        fields = "__all__"

        read_only_fields = [
            "id",
            "created_at",
        ]


# ============================================================
# SPECIFICATION
# ============================================================

class AdPropertySpecificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertySpecification
        fields = "__all__"

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


# ============================================================
# BROCHURE
# ============================================================

class AdPropertyBrochureSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertyBrochure
        fields = "__all__"

        read_only_fields = [
            "id",
            "uploaded_at",
        ]


# ============================================================
# MAIN PROPERTY
# ============================================================

class AdPropertySerializer(serializers.ModelSerializer):

    hero_images = AdProperty_imagesSerializer(
        many=True,
        read_only=True
    )

    builder_details = AdPropertyBuilderDetailsSerializer(
        read_only=True
    )

    configurations = AdPropertyConfigurationSerializer(
        many=True,
        read_only=True
    )

    location_advantages = (
        AdPropertyLocationAdvantageSerializer(
            many=True,
            read_only=True
        )
    )

    property_highlights = AdPropertyHighlightSerializer(
        many=True,
        read_only=True
    )

    property_amenities = AdPropertyAmenitySerializer(
        many=True,
        read_only=True
    )

    specifications = AdPropertySpecificationSerializer(
        many=True,
        read_only=True
    )

    brochures = AdPropertyBrochureSerializer(
        many=True,
        read_only=True
    )

    category_name = serializers.CharField(
        source="category_id.category",
        read_only=True
    )

    user_first_name = serializers.CharField(
        source="user_id.first_name",
        read_only=True
    )

    user_last_name = serializers.CharField(
        source="user_id.last_name",
        read_only=True
    )

    user_mobile_no = serializers.CharField(
        source="user_id.mobile_no",
        read_only=True
    )

    user_email = serializers.EmailField(
        source="user_id.email",
        read_only=True
    )

    class Meta:
        model = AdProperty
        fields = "__all__"





class AdPropertyRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdProperty
        fields = [
            "user_id",
            "category_id",
            "mobile_no",
            "admin_mobile",
            "Admin_status",

            "property_name",
            "property_type",
            "type",

            "address",
            "city",
            "location",
            "landmark",

            "lat",
            "long",

            "possession_date",

            "description",
            "tags",

            "min_budget",
            "max_budget",

            "min_acres",
            "max_acres",

            "ratio",
            "floor",
            "roadwidth",

            "site_area",
            "length",
            "width",
            "units",
            "buildup_area",

            "posted_by",
            "price",
            "nearby",

            "no_of_floors",

            "rooms_count",
            "duplex_bedrooms",
            "bedrooms_count",
            "bathrooms_count",
            "shop_count",
            "house_count",

            "facing",
            "balcony",
            "power_backup",
            "gated_security",
            "borewell",
            "parking",
            "lift",

            "advance_payment",

            "status",
            "adstart_date",
            "adend_date",
            "boost_date",
        ]


class AdProperty_imagesUploadSerializer(serializers.Serializer):

    images = serializers.ListField(
        child=serializers.ImageField(),
        required=True
    )




class AdPropertyBuilderDetailsRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertyBuilderDetails

        fields = [
            "builder_name",
            "city",
            "projects_completed",
            "ongoing_projects",
        ]



class AdPropertyConfigurationRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertyConfiguration

        fields = [
            "bhk_type",
            "carpet_area",
            "built_up_area",
            "super_built_up_area",
            "price",
            "facing",
            "bathrooms",
            "balcony",
            "parking",
        ]




class AdPropertyFloorPlanRequestSerializer(serializers.Serializer):

    plan_type = serializers.ChoiceField(
        choices=["2D", "3D"]
    )

    image = serializers.ImageField()



class AdPropertyLocationAdvantageRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertyLocationAdvantage

        fields = [
            "place_name",
            "distance",
            "travel_time",
            "order",
        ]


class AdPropertyHighlightRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertyHighlight

        fields = [
            "name",
            "icon",
            "order",
            "is_active",
        ]


class AdPropertyAmenityRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertyAmenity

        fields = [
            "name",
            "icon",
            "order",
            "is_active",
        ]



class AdPropertySpecificationRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = AdPropertySpecification

        fields = [
            "name",
            "value",
            "order",
        ]


class AdPropertyBrochureRequestSerializer(serializers.Serializer):

    title = serializers.CharField(
        max_length=200
    )

    document = serializers.FileField()



class AdPropertyCombinedRequestSerializer(serializers.Serializer):

    # ========================================================
    # MAIN PROPERTY
    # ========================================================

    user_id = serializers.IntegerField(
        required=True
    )

    category_id = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    mobile_no = serializers.CharField(
        required=False,
        allow_blank=True
    )

    admin_mobile = serializers.CharField(
        required=False,
        allow_blank=True
    )

    property_name = serializers.CharField(
        required=True
    )

    property_type = serializers.CharField(
        required=True
    )

    type = serializers.CharField(
        required=False,
        allow_blank=True
    )

    address = serializers.CharField(
        required=False,
        allow_blank=True
    )

    city = serializers.CharField(
        required=False,
        allow_blank=True
    )

    location = serializers.CharField(
        required=False,
        allow_blank=True
    )

    landmark = serializers.CharField(
        required=False,
        allow_blank=True
    )

    lat = serializers.CharField(
        required=False,
        allow_blank=True
    )

    long = serializers.CharField(
        required=False,
        allow_blank=True
    )

    possession_date = serializers.DateField(
        required=False,
        allow_null=True
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True
    )

    tags = serializers.CharField(
        required=False,
        allow_blank=True
    )

    min_budget = serializers.FloatField(
        required=False,
        allow_null=True
    )

    max_budget = serializers.FloatField(
        required=False,
        allow_null=True
    )

    posted_by = serializers.CharField(
        required=False,
        allow_blank=True
    )

    price = serializers.FloatField(
        required=False,
        allow_null=True
    )

    no_of_floors = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    status = serializers.BooleanField(
        required=False
    )

    # ========================================================
    # NESTED JSON
    # ========================================================

    builder_details = serializers.CharField(
        required=False,
        help_text=(
            'JSON string. Example: '
            '{"builder_name":"ABC Developers",'
            '"city":"Hyderabad",'
            '"projects_completed":25,'
            '"ongoing_projects":5}'
        )
    )

    configurations = serializers.CharField(
        required=False,
        help_text=(
            'JSON array containing BHK configurations.'
        )
    )

    location_advantages = serializers.CharField(
        required=False,
        help_text=(
            'JSON array. Maximum 8 locations.'
        )
    )

    highlights = serializers.CharField(
        required=False,
        help_text=(
            'JSON array of property highlights.'
        )
    )

    amenities = serializers.CharField(
        required=False,
        help_text=(
            'JSON array of property amenities.'
        )
    )

    specifications = serializers.CharField(
        required=False,
        help_text=(
            'JSON array of specification key/value pairs.'
        )
    )

    # ========================================================
    # HERO IMAGES
    # ========================================================

    hero_images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        help_text="Maximum 5 hero images."
    )

    # ========================================================
    # CONFIGURATION FLOOR PLANS
    # ========================================================

    configuration_0_2d = serializers.ImageField(
        required=False,
        help_text="2D floor plan for configurations[0]."
    )

    configuration_0_3d = serializers.ImageField(
        required=False,
        help_text="3D floor plan for configurations[0]."
    )

    configuration_1_2d = serializers.ImageField(
        required=False,
        help_text="2D floor plan for configurations[1]."
    )

    configuration_1_3d = serializers.ImageField(
        required=False,
        help_text="3D floor plan for configurations[1]."
    )

    configuration_2_2d = serializers.ImageField(
        required=False,
        help_text="2D floor plan for configurations[2]."
    )

    configuration_2_3d = serializers.ImageField(
        required=False,
        help_text="3D floor plan for configurations[2]."
    )

    configuration_3_2d = serializers.ImageField(
        required=False,
        help_text="2D floor plan for configurations[3]."
    )

    configuration_3_3d = serializers.ImageField(
        required=False,
        help_text="3D floor plan for configurations[3]."
    )

    configuration_4_2d = serializers.ImageField(
        required=False,
        help_text="2D floor plan for configurations[4]."
    )

    configuration_4_3d = serializers.ImageField(
        required=False,
        help_text="3D floor plan for configurations[4]."
    )

    # ========================================================
    # BROCHURES
    # ========================================================

    brochure_titles = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Brochure titles matching the brochure files."
    )

    brochures = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        help_text="PDF brochure files."
    )


