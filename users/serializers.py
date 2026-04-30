from rest_framework import serializers
from .models import *
from property.models import *
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.hashers import make_password


class rolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = rolePermission
        fields = '__all__'


class RoleSerializer(serializers.ModelSerializer):
    role_permission = rolePermissionSerializer(many=True, read_only=True)
    class Meta:
        model = Role
        fields = '__all__'


class VendorWorkImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorWorkImage
        fields = '__all__'        

        
class VendorSerializer(serializers.ModelSerializer):
    work_images = VendorWorkImageSerializer(many=True, read_only=True)
    new_work_images = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)
   
    class Meta:
        model = Vendors
        fields = '__all__'

    def create(self, validated_data):
        new_images = validated_data.pop('new_work_images', [])        
        vendor_instance = Vendors.objects.create(**validated_data)

        for image in new_images:
            VendorWorkImage.objects.create(vendor=vendor_instance, image=image)
        
        return vendor_instance




class best_dealsSerializer(serializers.ModelSerializer):
    class Meta:
        model = best_deals
        fields = '__all__'


class consultant_reqSerializer(serializers.ModelSerializer):
    class Meta:
        model = consultant_req
        fields = '__all__'


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'



class Enquiry_FormSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enquiry_Form
        fields = '__all__'


class user_cartSerializer(serializers.ModelSerializer):
    class Meta:
        model = user_cart
        fields = '__all__'



class activity_tblSerializer(serializers.ModelSerializer):
    class Meta:
        model = activity_tbl
        fields = '__all__'


class notificationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = notifications
        fields = '__all__'


class sub_userSerializer(serializers.ModelSerializer):
    class Meta:
        model = sub_user
        fields = '__all__'


class UserAddOnSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddOn
        fields = '__all__'


class UserFeaturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFeatures
        fields = '__all__'


class Property_imagesSerializer1(serializers.ModelSerializer):
    class Meta:
        model = Property_images
        fields = '__all__'


class PropertySerializer1(serializers.ModelSerializer):
    property_images = Property_imagesSerializer1(many=True, read_only=True)    

    class Meta:
        model = Property
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'       



class ResponsePropertyRequestSerializer1(serializers.ModelSerializer):    
    class Meta:
        model = ResponsePropertyRequest
        fields = '__all__'

class PropertyRequestSerializer1(serializers.ModelSerializer): 
    user_req = ResponsePropertyRequestSerializer1(many=True, read_only=True)   
    class Meta:
        model = PropertyRequest
        fields = '__all__'




class loghistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = loghistory
        fields = '__all__'


class iosUsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = iosUsers
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer): 

    class Meta:
        model = User
        fields = '__all__'   



class PasswordChangeSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True)



class loginserializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)    
    fcm_token = serializers.CharField(write_only=True) 


class forceloginserializer(serializers.Serializer):
    identifier = serializers.CharField()    
    fcm_token = serializers.CharField(write_only=True)  


class logoutserializer(serializers.Serializer):
    user_id = serializers.CharField()           


class sendotpserializer(serializers.Serializer):
    email = serializers.EmailField() 



class verifyotpserializer(serializers.Serializer):
    email = serializers.EmailField() 
    otp = serializers.CharField(write_only=True) 



class resetpasswordserializer(serializers.Serializer):
    email = serializers.EmailField() 
    otp = serializers.CharField(write_only=True) 
    password = serializers.CharField(write_only=True) 


class markAsReadSerializer(serializers.Serializer):
    notification_id = serializers.IntegerField(required=False)
    message_receiver = serializers.CharField(required=False)
    notification_type = serializers.CharField(required=False)




class markAsReadChartSerializer(serializers.Serializer):    
    user_id = serializers.CharField(required=False)
    receiver_id = serializers.CharField(required=False)
    property_id = serializers.CharField(required=False)



class UserGetUserTypeAPIViewSerializer(serializers.Serializer):    
    user_type = serializers.CharField(required=False)





class UpdateFreePlanTrialDaysSerializer(serializers.Serializer):
    trial_days = serializers.IntegerField(min_value=0, required=False, allow_null=True, help_text='Number of trial days for Free plans (optional, set to None to clear)')
    plan_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of subAdminplans IDs to update"
    )





class DeactivateFreePlansSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of user IDs to deactivate free plans for"
    )

