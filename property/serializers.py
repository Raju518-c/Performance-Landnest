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

    # Use the typed nested serializer so swagger shows exact keys instead of additionalPropX
    new_locations = NewLocationSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = PropertyRequest
        fields = '__all__'

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



