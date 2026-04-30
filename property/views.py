from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404
from django.db import models
from .models import *
from .serializers import *
import os
from datetime import datetime, timedelta
from django.utils import timezone

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema


@method_decorator(csrf_exempt, name='dispatch')
class PropertyCatView(APIView):

    def get(self, request, pk=None):
        try:
            if pk:
                category = Property_Cat.objects.get(pk=pk)
                serializer = Property_CatSerializer(category)
                return Response(serializer.data)
            else:
                categories = Property_Cat.objects.all()
                serializer = Property_CatSerializer(categories, many=True)
                return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)})

    @extend_schema(request=Property_CatSerializer)
    def post(self, request):        
        category = request.data.get('category')
        category_type = request.data.get('category_type')
        if Property_Cat.objects.filter(category=category, category_type=category_type).exists():
            return Response({'error': 'This category already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer = Property_CatSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({'message': 'Category created successfully', 'data': serializer.data}, status=status.HTTP_201_CREATED)
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(request=Property_CatSerializer)
    def put(self, request, pk):
        try:
            category = Property_Cat.objects.get(pk=pk)
            serializer = Property_CatSerializer(category, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({'message': 'Category updated successfully', 'data': serializer.data})
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Property_Cat.DoesNotExist:
            return Response({'error': 'Category not found'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        try:
            category = Property_Cat.objects.get(pk=pk)
            category.delete()
            return Response({'message': 'Category deleted successfully'})
        except Property_Cat.DoesNotExist:
            return Response({'error': 'Category not found'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class PropertyAPIView(APIView):
    def get(self, request, pk=None):
        if pk:
            try:
                property_obj = Property.objects.get(pk=pk)
                serializer = PropertySerializer(property_obj)
                return Response(serializer.data)
            except Property.DoesNotExist:
                return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            properties = Property.objects.all()
            serializer = PropertySerializer(properties, many=True)
            return Response(serializer.data)

    @extend_schema(request=PropertySerializer)
    def post(self, request):           
        request.data['status'] = True
        serializer = PropertySerializer(data=request.data)

        if serializer.is_valid():
            property_obj = serializer.save()

            all_users = User.objects.all().exclude(user_id=property_obj.user_id_id)

            for i in all_users:
                notifications.objects.create(
                    message_sender=property_obj.user_id,
                    message_receiver=i,
                    property_id=property_obj,
                    property_type=property_obj.type,
                    notification_type="general",
                    message=f"New property added by {property_obj.user_id.username}",
                    action_from_table="Property", 
                    action_tbl_id=str(property_obj.pk)
                )

            return Response({'message': 'Property created successfully', 'data': serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @extend_schema(request=PropertySerializer)
    def put(self, request, pk):
        try:
            property_obj = Property.objects.get(pk=pk)
        except Property.DoesNotExist:
            return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)


        deleted_ids = request.data.get('deleted_image_ids', '')
        deleted_ids = [int(i.strip()) for i in deleted_ids.split(',') if i.strip().isdigit()]
        

        for img_id in deleted_ids:
            try:
                image = Property_images.objects.get(id=img_id, property=property_obj)
                image_path = image.image.path

                if os.path.exists(image_path):
                    os.remove(image_path)
                image.delete()
            except Property_images.DoesNotExist:
                return Response(
                    {'error': f'Image with ID {img_id} not found for this property.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {'error': f'Failed to delete image {img_id}: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )




        # Save property and add new images
        serializer = PropertySerializer(property_obj, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()

            # Handle new images
            new_images = request.FILES.getlist('new_property_images')
            for image in new_images:
                Property_images.objects.create(property=property_obj, image=image)

            return Response({'message': 'Property updated successfully', 'data': serializer.data}, status=200)
        else:
            print("Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=400)





    def delete(self, request, pk):
        try:
            property_obj = Property.objects.get(pk=pk)
            property_obj.delete()
            return Response({'message': 'Property deleted successfully'})
        except Property.DoesNotExist:
            return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)



@method_decorator(csrf_exempt, name='dispatch')
class GetUserProperty(APIView):
    def get(self, request, user_id):        
        try:
            property_obj = Property.objects.filter(user_id=user_id)
            serializer = PropertySerializer(property_obj, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class GetPropertyType(APIView):
    def get(self, request, user_id, type):        
        try:
            property_obj = Property.objects.filter(user_id=user_id, type=type)
            serializer = PropertySerializer(property_obj, many=True)
            return Response({'count': property_obj.count(), 'properties': serializer.data}, status=status.HTTP_200_OK)            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@method_decorator(csrf_exempt, name='dispatch')
class BulkPropertyUpdateAPIView(APIView):

    @extend_schema(request=PropertySerializer)    
    def put(self, request):
        data = request.data

        if not isinstance(data, list):
            return Response({'error': 'Expected a list of property objects'}, status=status.HTTP_400_BAD_REQUEST)

        updated_properties = []
        errors = []

        for item in data:
            pk = item.get('property_id')
            if not pk:
                errors.append({'error': 'property_id is required for each item'})
                continue

            try:
                property_instance = Property.objects.get(pk=pk)
                serializer = PropertySerializer(property_instance, data=item, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    updated_properties.append(serializer.data)
                else:
                    errors.append({'property_id': pk, 'errors': serializer.errors})
            except Property.DoesNotExist:
                errors.append({'property_id': pk, 'error': 'Property not found'})

        response_data = {'updated': updated_properties}
        if errors:
            response_data['errors'] = errors

        return Response(response_data, status=status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS)





@method_decorator(csrf_exempt, name='dispatch')
class BoostPropertyAPIView(APIView):

    @extend_schema(request=boostpropertyserializer)    
    def post(self, request):
        try:
            user_id = request.data.get('user_id')

            if not user_id:
                return Response({"status": False, "message": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            properties = Property.objects.filter(user_id=user_id)

            if not properties.exists():
                return Response({"status": False, "message": "No property found for this user"}, status=status.HTTP_404_NOT_FOUND)

            today = timezone.now() + timedelta(hours=5, minutes=30)                            
            properties.update(boost_date=today)

            serializer = PropertySerializer(properties, many=True)

            return Response({
                "status": True,
                "message": f"Boost date updated to {today} for {properties.count()} properties.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": False,
                "message": f"An error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@method_decorator(csrf_exempt, name='dispatch')
class PropertyRequestCRUD(APIView):

    @extend_schema(request=PropertyRequestSerializer)    
    def post(self, request):
        try:
            serializer = PropertyRequestSerializer(data=request.data)
            if serializer.is_valid():

                req_rec = serializer.save()

                all_users = User.objects.all().exclude(user_id=req_rec.user_id_id)

                for i in all_users:
                    notifications.objects.create(
                        message_sender=req_rec.user_id,
                        message_receiver=i,
                        notification_type="general",
                        message=f"Property requested by {req_rec.user_id.username}",
                        action_from_table="PropertyRequest", 
                        action_tbl_id=str(req_rec.pk)
                    )

                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def get(self, request, pk=None):
        try:            
            if pk:
                obj = PropertyRequest.objects.get(pk=pk)
                serializer = PropertyRequestSerializer(obj)
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            objs = PropertyRequest.objects.all()
            serializer = PropertyRequestSerializer(objs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except PropertyRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(request=PropertyRequestSerializer)
    def put(self, request, pk):
        try:
            obj = PropertyRequest.objects.get(pk=pk)

            # ---------- HANDLE DELETED LOCATIONS ----------
            deleted_location_ids = request.data.get('deleted_location_ids', '')
            deleted_location_ids = [
                int(i.strip()) for i in deleted_location_ids.split(',')
                if i.strip().isdigit()
            ]

            for loc_id in deleted_location_ids:
                try:
                    loc_obj = PropertyRequestLocations.objects.get(loc_id=loc_id, req_id=obj)
                    loc_obj.delete()
                except PropertyRequestLocations.DoesNotExist:
                    return Response(
                        {"error": f"Location ID {loc_id} not found for this request"},
                        status=status.HTTP_404_NOT_FOUND
                    )

            # ---------- PARTIAL UPDATE (this will also handle new_locations via serializer.update) ----------
            serializer = PropertyRequestSerializer(obj, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except PropertyRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    
    def delete(self, request, pk):
        try:
            obj = PropertyRequest.objects.get(pk=pk)
            obj.delete()
            return Response({"message": "Deleted successfully"}, status=status.HTTP_200_OK)

        except PropertyRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class ResponsePropertyRequestCRUD(APIView):
    
    @extend_schema(request=ResponsePropertyRequestSerializer)    
    def post(self, request):
        try:
            serializer = ResponsePropertyRequestSerializer(data=request.data)
            if serializer.is_valid():

                res_rec = serializer.save()

                notifications.objects.create(
                    message_sender=res_rec.user_id,
                    message_receiver=res_rec.req_id.user_id,                        
                    notification_type="general",
                    message=f"{res_rec.user_id.username} if responded to Property request",
                    action_from_table="ResponsePropertyRequest", 
                    action_tbl_id=str(res_rec.pk)
                )


                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def get(self, request, pk=None):
        try:
            if pk:
                obj = ResponsePropertyRequest.objects.get(pk=pk)
                serializer = ResponsePropertyRequestSerializer(obj)
                return Response(serializer.data, status=status.HTTP_200_OK)

            objs = ResponsePropertyRequest.objects.all()
            serializer = ResponsePropertyRequestSerializer(objs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ResponsePropertyRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(request=ResponsePropertyRequestSerializer)    
    def put(self, request, pk):
        try:
            obj = ResponsePropertyRequest.objects.get(pk=pk)
            serializer = ResponsePropertyRequestSerializer(obj, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except ResponsePropertyRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def delete(self, request, pk):
        try:
            obj = ResponsePropertyRequest.objects.get(pk=pk)
            obj.delete()
            return Response({"message": "Deleted successfully"}, status=status.HTTP_200_OK)

        except ResponsePropertyRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@method_decorator(csrf_exempt, name='dispatch')
class BankAuctionPropertyView(APIView):

    def get(self, request, pk=None):
        try:
            if pk:
                obj = BankAuctionProperty.objects.get(pk=pk)
                serializer = BankAuctionPropertySerializer(obj)
                return Response(serializer.data)
            else:
                all_data = BankAuctionProperty.objects.all()
                serializer = BankAuctionPropertySerializer(all_data, many=True)
                return Response(serializer.data)
        except BankAuctionProperty.DoesNotExist:
            return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(request=BankAuctionPropertySerializer)
    def post(self, request):
        try:
            serializer = BankAuctionPropertySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {'message': 'Auction property created successfully', 'data': serializer.data},
                    status=status.HTTP_201_CREATED
                )
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(request=BankAuctionPropertySerializer)
    def put(self, request, pk):
        try:
            obj = BankAuctionProperty.objects.get(pk=pk)

            # -------- DELETE DOCUMENTS --------
            deleted_doc_ids = request.data.get("deleted_doc_ids", "")
            deleted_doc_ids = [
                int(x.strip()) for x in deleted_doc_ids.split(",") if x.strip().isdigit()
            ]

            for doc_id in deleted_doc_ids:
                try:
                    doc_obj = BankAuctionPropertyDocs.objects.get(doc_id=doc_id, bankpro_id=obj)
                    doc_obj.delete()
                except BankAuctionPropertyDocs.DoesNotExist:
                    return Response(
                        {"error": f"Document ID {doc_id} not found for this property"},
                        status=status.HTTP_404_NOT_FOUND
                    )


            serializer = BankAuctionPropertySerializer(obj, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(
                    {'message': 'Auction property updated successfully', 'data': serializer.data},
                    status=status.HTTP_200_OK
                )
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except BankAuctionProperty.DoesNotExist:
            return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, pk):
        try:
            obj = BankAuctionProperty.objects.get(pk=pk)
            obj.delete()
            return Response({'message': 'Auction property deleted successfully'}, status=status.HTTP_200_OK)

        except BankAuctionProperty.DoesNotExist:
            return Response({'error': 'Record not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@method_decorator(csrf_exempt, name='dispatch')
class LeasePropertyListAPIView(APIView):
    def get(self, request):
        properties = Property.objects.filter(type__iexact='lease', Admin_status='Approved')
        serializer = PropertySerializer(properties, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




@method_decorator(csrf_exempt, name='dispatch')
class SellPropertiesByAdminAPIView(APIView):
    """
    Get all properties with type='sell' where user is Admin role
    """
    def get(self, request):
        try:
            properties = Property.objects.filter(
                type__iexact='sell',
                user_id__role='Admin'
            )
            serializer = PropertySerializer(properties, many=True)
            return Response({
                'count': properties.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@method_decorator(csrf_exempt, name='dispatch')
class SellPropertiesByNonAdminboxAPIView(APIView):
    """
    Viewport-based spatial filtering.
    
    Query params:
      - south, north, west, east  → bounding box (required for viewport mode)
      - page, page_size            → fallback pagination (default 20)
    
    If bbox params are present → return properties within bounds (no limit).
    If no bbox → return first `page_size` properties (initial load).
    """

    def get(self, request):
        try:
            base_qs = (
                Property.objects
                .filter(type__iexact='sell', Admin_status='Approved')
                .exclude(user_id__role='Admin')
                .exclude(lat__isnull=True)
                .exclude(long__isnull=True)
            )

            south = request.query_params.get('south')
            north = request.query_params.get('north')
            west  = request.query_params.get('west')
            east  = request.query_params.get('east')

            bbox_provided = all([south, north, west, east])

            if bbox_provided:
                # ── Viewport query ──────────────────────────────────────
                try:
                    south, north = float(south), float(north)
                    west,  east  = float(west),  float(east)
                except ValueError:
                    return Response(
                        {'error': 'Invalid bbox params'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                properties = base_qs.filter(
                    lat__gte=south, lat__lte=north,
                    long__gte=west, long__lte=east,
                )

            else:
                # ── Initial load: first 20 only ─────────────────────────
                page_size  = int(request.query_params.get('page_size', 20))
                properties = base_qs.order_by('-boost_date', '-created_at')[:page_size]

            serializer = PropertySerializer(properties, many=True)
            return Response(
                {'count': len(serializer.data), 'data': serializer.data},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@method_decorator(csrf_exempt, name='dispatch')
class SellPropertiesByNonAdminCoordinatesAPIView(APIView):
    """
    Get sell properties by non-admin with only coordinates and minimal metadata.
    """
    def get(self, request):
        try:
            properties = Property.objects.filter(
                type__iexact='sell', Admin_status='Approved'
            ).exclude(
                user_id__role='Admin'
            )
            serializer = SellPropertyCoordinatesSerializer(properties, many=True)
            return Response({
                'count': properties.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class SellPropertiesByNonAdminSummaryAPIView(APIView):
    """
    Get sell properties by non-admin with selected summary fields and images.
    """
    def get(self, request, pk):
        try:
            properties = Property.objects.get(pk=pk)
            serializer = SellPropertySummarySerializer(properties)
            return Response({
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@method_decorator(csrf_exempt, name='dispatch')
class BestDealApprovedPropertiesAPIView(APIView):
    """
    Get all properties with type='best-deal' and Admin_status='Approved'
    """
    def get(self, request):
        try:
            properties = Property.objects.filter(
                type__iexact='best-deal',
                Admin_status='Approved'
            )
            serializer = PropertySerializer(properties, many=True)
            return Response({
                'count': properties.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class FilteredPropertyAPIView(APIView):
    """
    Get properties with dynamic filters from payload
    """
    def post(self, request):
        try:
            include = request.data.get('include', {})
            exclude = request.data.get('exclude', {})

            # Get model fields for type checking
            model_fields = {f.name: f for f in Property._meta.get_fields() if hasattr(f, 'name')}

            def build_kwargs(data_dict):
                kwargs = {}
                for k, v in data_dict.items():
                    if k in model_fields:
                        field = model_fields[k]
                        if isinstance(field, (models.CharField, models.TextField)):
                            kwargs[f"{k}__iexact"] = v
                        else:
                            kwargs[f"{k}__exact"] = v
                    # If field not found, skip or handle error
                return kwargs

            filter_kwargs = build_kwargs(include)
            exclude_kwargs = build_kwargs(exclude)

            if filter_kwargs and exclude_kwargs:
                properties = Property.objects.filter(**filter_kwargs).exclude(**exclude_kwargs)
            elif filter_kwargs:
                properties = Property.objects.filter(**filter_kwargs)
            elif exclude_kwargs:
                properties = Property.objects.exclude(**exclude_kwargs)
            else:
                properties = Property.objects.all()

            serializer = PropertySerializer(properties, many=True)

            return Response({
                'count': properties.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





@method_decorator(csrf_exempt, name='dispatch')
class FilteredBankAuctionPropertyAPIView(APIView):
    """
    Get properties with dynamic filters from payload
    """
    def post(self, request):
        try:
            include = request.data.get('include', {})
            exclude = request.data.get('exclude', {})

            # Get model fields for type checking
            model_fields = {f.name: f for f in BankAuctionProperty._meta.get_fields() if hasattr(f, 'name')}

            def build_kwargs(data_dict):
                kwargs = {}
                for k, v in data_dict.items():
                    if k in model_fields:
                        field = model_fields[k]
                        if isinstance(field, (models.CharField, models.TextField)):
                            kwargs[f"{k}__iexact"] = v
                        else:
                            kwargs[f"{k}__exact"] = v
                    # If field not found, skip or handle error
                return kwargs

            filter_kwargs = build_kwargs(include)
            exclude_kwargs = build_kwargs(exclude)

            if filter_kwargs and exclude_kwargs:
                properties = BankAuctionProperty.objects.filter(**filter_kwargs).exclude(**exclude_kwargs)
            elif filter_kwargs:
                properties = BankAuctionProperty.objects.filter(**filter_kwargs)
            elif exclude_kwargs:
                properties = BankAuctionProperty.objects.exclude(**exclude_kwargs)
            else:
                properties = BankAuctionProperty.objects.all()

            serializer = BankAuctionPropertySerializer(properties, many=True)

            return Response({
                'count': properties.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@method_decorator(csrf_exempt, name='dispatch')
class SellPropertiesByNonAdminAPIView(APIView):
    """
    Get all properties with type='sell' where user is NOT Admin role
    """
    def get(self, request):
        try:
            properties = Property.objects.filter(
                type__iexact='sell', Admin_status='Approved'
            ).exclude(
                user_id__role='Admin'
            )
            serializer = SellPropertySummarySerializer(properties, many=True)
            return Response({
                'count': properties.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

