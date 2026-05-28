from celery import shared_task
from .models import *
from datetime import datetime, timedelta
from django.utils import timezone
from .serializers import *
from property.models import Property 
from django.db.models import Q

@shared_task
def check_expired_subscriptions():
    """
    Check for expired subscriptions and update user status and related data.
    This task runs every 5 minutes via Celery Beat.
    """
    all_users = sub_user.objects.filter(status=True)                   

    for user in all_users:
        try:
            today = timezone.now() + timedelta(hours=5, minutes=30)

            if user.expired_date and today >= user.expired_date:
                # 1. Set status=False
                print(f'Processing expired subscription for user {user.user_id}, type: {user.user_type}')
                print(f'Expired date: {user.expired_date}, Today: {today}')
                print('user.user_type', user.user_type)
                print('user.expired_date', user.expired_date)
                print('today', today)
                serializer = sub_userSerializer(user, data={'status': False}, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                
                try:
                    features = UserFeatures.objects.filter(user_id=user.user_id, user_type=user.user_type)
                    features.delete()
                    print(f'Deleted UserFeatures for user {user.user_id}')
                except UserFeatures.DoesNotExist:
                    continue
                except Exception as e:
                    print(f"Error deleting UserFeatures for user {user.user_id}: {e}")

                try: 
                    if user.user_type == 'Individual Owner/Builder' or user.user_type == 'Landlord' or user.user_type == 'Agent':
                        if not user.no_of_properties_unlimited:                                                   
                            try:
                                if user.user_type == 'Individual Owner/Builder':
                                    all_props = Property.objects.filter(user_id=user.user_id,status=True).filter((Q(posted_by='Owner') | Q(posted_by='Builder')) &(Q(type='sell') | Q(type='best-deal')))
                                elif user.user_type == 'Landlord':
                                    all_props = Property.objects.filter(user_id=user.user_id,status=True).filter(Q(type='rent') | Q(type='lease'))
                                elif user.user_type == 'Agent':
                                    all_props = Property.objects.filter(user_id=user.user_id,status=True, posted_by = 'Agent').filter(Q(type='sell') | Q(type='best-deal'))
                            except Exception as e:
                                print(f"Error querying properties for user {user.user_id}: {e}")
                                all_props = None

                            if all_props:
                                for prop in all_props:
                                    prop.status = False
                                    prop.save()
                                print(f'Deactivated {len(all_props)} properties for user {user.user_id}')
                    else:
                        if not user.buyer_no_unlimited:   
                            try:                                 
                                if user.user_type == 'Buyer':
                                    all_cart = user_cart.objects.filter(user_id=user.user_id, status=True, activity_as = 'Buyer')
                                elif user.user_type == 'Tenant':
                                    all_cart = user_cart.objects.filter(user_id=user.user_id, status=True, activity_as = 'Tenant')
                            except Exception as e:
                                print(f"Error querying cart for user {user.user_id}: {e}")
                                all_cart = None

                            if all_cart:
                                for i in all_cart:
                                    i.status = False
                                    i.save()
                                print(f'Deactivated {len(all_cart)} cart items for user {user.user_id}')

                            try:                                 
                                if user.user_type == 'Buyer':
                                    all_act = activity_tbl.objects.filter(user_id=user.user_id, status=True, activity_as = 'Buyer')
                                elif user.user_type == 'Tenant':
                                    all_act = activity_tbl.objects.filter(user_id=user.user_id, status=True, activity_as = 'Tenant')
                            except Exception as e:
                                print(f"Error querying activities for user {user.user_id}: {e}")
                                all_act = None

                            if all_act:
                                for i in all_act:
                                    i.status = False
                                    i.save()
                                print(f'Deactivated {len(all_act)} activities for user {user.user_id}')

                except Exception as e:
                    print(f"Error updating property visibility for user {user.user_id}: {e}")
                    
        except Exception as e:
            print(f"Error processing user {user.sub_id}: {e}") 

    return f"Processed {len(all_users)} users for expired subscriptions"

# import threading
# import time
# from .models import *
# from datetime import datetime, timedelta
# from django.utils import timezone
# from .serializers import *
# from property.models import Property 
# from django.db.models import Q

# def print_every_5_seconds():

#     while True:
        
#         all_users = sub_user.objects.filter(status = True)                   

#         for user in all_users:
#             try:
#                 today = timezone.now() + timedelta(hours=5, minutes=30)

#                 if user.expired_date and today >= user.expired_date:
#                     # 1. Set status=False
#                     print(f'Processing expired subscription for user {user.user_id}, type: {user.user_type}')
#                     print(f'Expired date: {user.expired_date}, Today: {today}')
#                     print('user.user_type', user.user_type)
#                     print('user.expired_date', user.expired_date)
#                     print('today', today)
#                     serializer = sub_userSerializer(user, data={'status': False}, partial=True)
#                     serializer.is_valid(raise_exception=True)
#                     serializer.save()
                    
#                     try:
#                         features = UserFeatures.objects.filter(user_id=user.user_id, user_type=user.user_type)
#                         print(f'Deleted UserFeatures for user {user.user_id}')
#                     except UserFeatures.DoesNotExist:
#                         continue

#                     features.delete()

#                     try: 
#                         if user.user_type == 'Individual Owner/Builder' or user.user_type == 'Landlord' or user.user_type == 'Agent':
#                             if not user.no_of_properties_unlimited:                                                   
#                                 print('1')
#                                 try:
#                                     if user.user_type == 'Individual Owner/Builder':
#                                         print('2')
#                                         all_props = Property.objects.filter(user_id=user.user_id,status=True).filter((Q(posted_by='Owner') | Q(posted_by='Builder')) &(Q(type='sell') | Q(type='best-deal')))
#                                     elif user.user_type == 'Landlord':
#                                         print('3')
#                                         all_props = Property.objects.filter(user_id=user.user_id,status=True).filter(Q(type='rent') | Q(type='lease'))
#                                     elif user.user_type == 'Agent':
#                                         print('4')
#                                         all_props = Property.objects.filter(user_id=user.user_id,status=True, posted_by = 'Agent').filter(Q(type='sell') | Q(type='best-deal'))
#                                 except:
#                                     all_props = None

#                                 if all_props:
#                                     for prop in all_props:
#                                         prop.status = False
#                                         prop.save()
#                         else:
#                             if not user.buyer_no_unlimited:   
#                                 try:                                 
#                                     if user.user_type == 'Buyer':
#                                         all_cart = user_cart.objects.filter(user_id=user.user_id, status=True, activity_as = 'Buyer')
#                                     elif user.user_type == 'Tenant':
#                                         all_cart = user_cart.objects.filter(user_id=user.user_id, status=True, activity_as = 'Tenant')
#                                 except:
#                                     all_cart = None

#                                 if all_cart:
#                                     for i in all_cart:
#                                         i.status = False
#                                         i.save()

#                                 try:                                 
#                                     if user.user_type == 'Buyer':
#                                         all_act = activity_tbl.objects.filter(user_id=user.user_id, status=True, activity_as = 'Buyer')
#                                     elif user.user_type == 'Tenant':
#                                         all_act = activity_tbl.objects.filter(user_id=user.user_id, status=True, activity_as = 'Tenant')
#                                 except:
#                                     all_act = None

#                                 if all_act:
#                                     for i in all_act:
#                                         i.status = False
#                                         i.save()

#                     except Exception as e:
#                         print(f"Error updating property visibility for user {user.user_id}: {e}")
#             except Exception as e:
#                 print(f"Error processing user {user.sub_id}: {e}") 
              

#         time.sleep(1)  


# def start_thread():
#     printer_thread = threading.Thread(target=print_every_5_seconds)
#     printer_thread.daemon = True
#     printer_thread.start()

