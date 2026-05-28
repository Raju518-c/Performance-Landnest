from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Q
from .models import *
from .serializers import *
import os
import re
from datetime import datetime, timedelta
from django.utils import timezone
import json

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from cache_config import (
    cache_manager, 
    get_total_property_requests_count, 
    get_looking_for_count, 
    update_total_property_requests_count, 
    update_looking_for_count,
    get_total_bank_auction_properties_count,
    update_total_bank_auction_properties_count,
    get_total_properties_count_fast,
    update_total_properties_count,
    get_property_type_count_fast,
    get_type_count_fast,
    get_property_filter_count_fast
)
from meilisearch_helpers import (
    get_meilisearch_bank_index, 
    MEILI_BANK_DISPLAYED, 
    MEILI_BANK_SEARCHABLE,
    get_meilisearch_property_index,
    MEILI_PROPERTY_DISPLAYED,
    MEILI_PROPERTY_SEARCHABLE,
    get_meilisearch_wanted_index,
    MEILI_WANTED_DISPLAYED,
    MEILI_WANTED_SEARCHABLE
)

def build_property_cache_key(search_query, property_type_filter, type_filter, page, page_size, chunk, chunk_number):
    safe_search = re.sub(r'[^A-Za-z0-9_]+', '_', (search_query or '').strip().lower()) if search_query else 'all'
    safe_prop_type = re.sub(r'[^A-Za-z0-9_]+', '_', (property_type_filter or '').strip().lower()) if property_type_filter else 'all'
    safe_type = re.sub(r'[^A-Za-z0-9_]+', '_', (type_filter or '').strip().lower()) if type_filter else 'all'
    return f"property_search_{safe_search}_{safe_prop_type}_{safe_type}_{page}_{page_size}_{chunk}_{chunk_number}"

def perform_meilisearch_properties(search_query, property_type_filter, type_filter, actual_offset, actual_page_size, price_min=None, price_max=None, exclude_role=None):
    index = get_meilisearch_property_index()
    if not index:
        return None, None

    filter_clauses = [
        'Admin_status = "Approved"'
    ]
    
    if exclude_role:
        filter_clauses.append(f'user_role != "{exclude_role}"')
    
    if property_type_filter:
        filter_clauses.append(f'property_type = "{property_type_filter}"')
    if type_filter:
        filter_clauses.append(f'type = "{type_filter}"')
    
    # Add price range filters
    if price_min is not None:
        filter_clauses.append(f'price >= {price_min}')
    if price_max is not None:
        filter_clauses.append(f'price <= {price_max}')

    options = {
        'filter': filter_clauses if filter_clauses else None,
        'attributesToRetrieve': MEILI_PROPERTY_DISPLAYED,
        'offset': actual_offset,
        'limit': actual_page_size,
        'matchingStrategy': 'all' if len(re.findall(r'\w+', search_query)) > 1 else 'last',
    }

    try:
        search_result = index.search(search_query, options)
        hits = search_result.get('hits', [])
        total_count = search_result.get('estimatedTotalHits') or search_result.get('nbHits') or len(hits)
        return hits[:actual_page_size], total_count
    except Exception:
        return None, None

def perform_db_search_properties(search_query, property_type_filter, type_filter, actual_offset, actual_page_size, price_min=None, price_max=None, exclude_role=None):
    # BASE FILTERS: Approved status is MANDATORY
    queryset = Property.objects.filter(
        Admin_status='Approved'
    )
    
    if exclude_role:
        queryset = queryset.exclude(user_id__role=exclude_role)
        
    queryset = queryset.select_related('user_id', 'category_id').only(
        'property_id', 'property_name', 'location', 'posted_by', 'property_type', 
        'type', 'facing', 'site_area', 'price', 'units', 'mobile_no',
        'user_id__first_name', 'user_id__last_name', 'user_id__mobile_no', 'user_id__email',
        'category_id__category', 'Admin_status'
    )
    
    if property_type_filter:
        queryset = queryset.filter(property_type__iexact=property_type_filter)
    if type_filter:
        queryset = queryset.filter(type__iexact=type_filter)
    
    # Add price range filters to DB search
    if price_min is not None:
        queryset = queryset.filter(price__gte=price_min)
    if price_max is not None:
        queryset = queryset.filter(price__lte=price_max)
    
    if search_query:
        search_query_lower = search_query.lower().strip()
        
        # Optimization: If query is exactly a known categorical value, use exact matching
        if search_query_lower in ['builder', 'agent', 'individual owner', 'individual owner/builder']:
            search_q = Q(posted_by__iexact=search_query_lower)
        elif search_query_lower in ['sell', 'rent', 'lease']:
            search_q = Q(type__iexact=search_query_lower)
        else:
            search_q = (
                Q(property_name__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(posted_by__icontains=search_query) |
                Q(property_type__icontains=search_query) |
                Q(type__icontains=search_query) |
                Q(category_id__category__icontains=search_query) |
                Q(user_id__first_name__icontains=search_query) |
                Q(user_id__last_name__icontains=search_query) |
                Q(facing__icontains=search_query)
            )
        
        # Numeric searches for BHK, Bedrooms, etc.
        digit_match = re.search(r'(\d+)', search_query)
        if digit_match:
            val = int(digit_match.group(1))
            if 'bhk' in search_query.lower():
                search_q |= Q(_1bhk_count=val) | Q(_2bhk_count=val) | Q(_3bhk_count=val) | Q(_4bhk_count=val)
            if 'bedroom' in search_query.lower():
                search_q |= Q(bedrooms_count=val)
            if 'flore' in search_query.lower() or 'floor' in search_query.lower():
                search_q |= Q(no_of_flores=val)
        
        queryset = queryset.filter(search_q)

    # Get total count for pagination with caching
    if search_query or price_min or price_max or exclude_role:
        # Cache the count for search results as it takes 30s+ for 800k records
        cache_key = f"search_count_{re.sub(r'[^A-Za-z0-9]+', '_', search_query.lower())}_{property_type_filter}_{type_filter}_{price_min}_{price_max}_{exclude_role}"
        total_count = cache_manager.get(cache_key)
        
        if total_count is None:
            total_count = queryset.count()
            cache_manager.set(cache_key, total_count, 3600)
        else:
            total_count = int(total_count)
    else:
        # For non-search/non-price queries, use the fast global count (which already has base filters applied in logic)
        total_count = get_total_properties_count_fast()

    objs = queryset.prefetch_related('property_images')[actual_offset:actual_offset + actual_page_size]
    
    data = []
    for obj in objs:
        data.append({
            'property_id': obj.property_id,
            'property_name': obj.property_name,
            'property_type': obj.property_type,
            'posted_by': obj.posted_by,
            'facing': obj.facing,
            'site_area': obj.site_area,
            'price': obj.price,
            'location': obj.location,
            'Admin_status': obj.Admin_status,
            'user_id': obj.user_id.user_id if obj.user_id else None,
            'user_first_name': obj.user_id.first_name if obj.user_id else '',
            'user_last_name': obj.user_id.last_name if obj.user_id else '',
            'user_mobile_no': obj.user_id.mobile_no if obj.user_id else '',
            'category_id': obj.category_id.category_id if obj.category_id else None,
            'category_name': obj.category_id.category if obj.category_id else '',
            'property_images': [{'id': img.id, 'image': img.image.name} for img in obj.property_images.all()]
        })
    
    return data, total_count

def build_wanted_property_cache_key(search_query, looking_for_filter, property_type_filter, page, page_size, chunk, chunk_number):
    safe_search = re.sub(r'[^A-Za-z0-9_]+', '_', (search_query or '').strip().lower()) if search_query else 'all'
    safe_looking = re.sub(r'[^A-Za-z0-9_]+', '_', (looking_for_filter or '').strip().lower()) if looking_for_filter else 'all'
    safe_prop_type = re.sub(r'[^A-Za-z0-9_]+', '_', (property_type_filter or '').strip().lower()) if property_type_filter else 'all'
    return f"wanted_search_{safe_search}_{safe_looking}_{safe_prop_type}_{page}_{page_size}_{chunk}_{chunk_number}"

def perform_meilisearch_property_requests(search_query, looking_for_filter, property_type_filter, actual_offset, actual_page_size):
    index = get_meilisearch_wanted_index()
    if not index:
        return None, None

    filter_clauses = []
    if looking_for_filter:
        filter_clauses.append(f'looking_for = "{looking_for_filter}"')
    if property_type_filter:
        filter_clauses.append(f'property_type = "{property_type_filter}"')

    options = {
        'filter': filter_clauses if filter_clauses else None,
        'attributesToRetrieve': MEILI_WANTED_DISPLAYED,
        'offset': actual_offset,
        'limit': actual_page_size,
        'matchingStrategy': 'all' if len(re.findall(r'\w+', search_query)) > 1 else 'last',
    }

    try:
        search_result = index.search(search_query, options)
        hits = search_result.get('hits', [])
        total_count = search_result.get('estimatedTotalHits') or search_result.get('nbHits') or len(hits)
        return hits[:actual_page_size], total_count
    except Exception:
        return None, None

def perform_db_search_property_requests(search_query, looking_for_filter, property_type_filter, actual_offset, actual_page_size):
    queryset = PropertyRequest.objects.all().select_related('user_id').prefetch_related('pro_loc').only(
        'req_id', 'user_id', 'looking_for', 'property_type', 'min_budget', 'max_budget', 
        'no_of_bedrooms', 'area', 'units', 'created_at', 'updated_at',
        'user_id__first_name', 'user_id__last_name', 'user_id__mobile_no', 'user_id__email'
    )
    
    if looking_for_filter:
        queryset = queryset.filter(looking_for__iexact=looking_for_filter)
    if property_type_filter:
        queryset = queryset.filter(property_type__iexact=property_type_filter)
    
    if search_query:
        search_query_lower = search_query.lower().strip()
        
        # Optimization: If query is exactly a known categorical value, use exact matching
        if search_query_lower in ['purchase', 'rent', 'lease', 'jv/jd', 'build to suit']:
            search_q = Q(looking_for__iexact=search_query_lower)
        else:
            search_q = (
                Q(user_id__first_name__icontains=search_query) |
                Q(user_id__last_name__icontains=search_query) |
                Q(looking_for__icontains=search_query) |
                Q(property_type__icontains=search_query) |
                Q(pro_loc__location__icontains=search_query) |
                Q(comment__icontains=search_query)
            )
        
        # Numeric searches for BHK/Bedrooms
        digit_match = re.search(r'(\d+)', search_query)
        if digit_match:
            val = int(digit_match.group(1))
            if 'bedroom' in search_query.lower():
                search_q |= Q(no_of_bedrooms=val)
        
        queryset = queryset.filter(search_q).distinct()

    # Cache the count for search results as it's slow for large datasets
    if search_query:
        cache_key = f"wanted_search_count_{re.sub(r'[^A-Za-z0-9]+', '_', search_query.lower())}_{looking_for_filter}_{property_type_filter}"
        total_count = cache_manager.get(cache_key)
        
        if total_count is None:
            total_count = queryset.count()
            cache_manager.set(cache_key, total_count, 3600)
        else:
            total_count = int(total_count)
    else:
        total_count = get_total_property_requests_count()

    objs = queryset[actual_offset:actual_offset + actual_page_size]
    
    data = []
    for obj in objs:
        loc = obj.pro_loc.first()
        data.append({
            'req_id': obj.req_id,
            'user_id': obj.user_id_id,
            'user_first_name': obj.user_id.first_name if obj.user_id else '',
            'user_last_name': obj.user_id.last_name if obj.user_id else '',
            'user_mobile_no': obj.user_id.mobile_no if obj.user_id else '',
            'user_email': obj.user_id.email if obj.user_id else '',
            'looking_for': obj.looking_for,
            'property_type': obj.property_type,
            'min_budget': obj.min_budget,
            'max_budget': obj.max_budget,
            'no_of_bedrooms': obj.no_of_bedrooms,
            'location': loc.location if loc else '-',
            'area': obj.area,
            'units': obj.units,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
        })
    
    return data, total_count

def build_bank_search_cache_key(search_query, property_type_filter, page, page_size, chunk, chunk_number):
    safe_search = re.sub(r'[^A-Za-z0-9_]+', '_', (search_query or '').strip().lower()) if search_query else 'all'
    safe_type = re.sub(r'[^A-Za-z0-9_]+', '_', (property_type_filter or '').strip().lower()) if property_type_filter else 'all'
    return f"bank_search_{safe_search}_{safe_type}_{page}_{page_size}_{chunk}_{chunk_number}"

def perform_meilisearch_bank_properties(search_query, property_type_filter, actual_offset, actual_page_size):
    index = get_meilisearch_bank_index()
    if not index:
        return None, None

    filter_clauses = []
    if property_type_filter:
        filter_clauses.append(f'property_type = "{property_type_filter}"')

    options = {
        'filter': filter_clauses if filter_clauses else None,
        'attributesToRetrieve': MEILI_BANK_DISPLAYED,
        'offset': actual_offset,
        'limit': actual_page_size,
        'matchingStrategy': 'all' if len(re.findall(r'\w+', search_query)) > 1 else 'last',
    }

    try:
        search_result = index.search(search_query, options)
        hits = search_result.get('hits', [])
        # Simple ratio match check if needed
        total_count = search_result.get('estimatedTotalHits') or search_result.get('nbHits') or len(hits)
        return hits[:actual_page_size], total_count
    except Exception:
        return None, None

def perform_db_search_bank_properties(search_query, property_type_filter, actual_offset, actual_page_size):
    queryset = BankAuctionProperty.objects.all()
    if property_type_filter:
        queryset = queryset.filter(property_type__icontains=property_type_filter)
    
    if search_query:
        search_query_lower = search_query.lower().strip()
        
        # Optimization: Use exact matching for property type if it matches exactly
        if search_query_lower in ['plot', 'land', 'villa', 'flat', 'apartment', 'house']:
            search_q = Q(property_type__iexact=search_query_lower)
        else:
            search_q = (
                Q(bank_name__icontains=search_query) |
                Q(property_type__icontains=search_query) |
                Q(action_type__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(city_town__icontains=search_query) |
                Q(area_town__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        queryset = queryset.filter(search_q)

    # Cache the count for search results
    if search_query:
        cache_key = f"bank_search_count_{re.sub(r'[^A-Za-z0-9]+', '_', search_query.lower())}_{property_type_filter}"
        total_count = cache_manager.get(cache_key)
        if total_count is None:
            total_count = queryset.count()
            cache_manager.set(cache_key, total_count, 3600)
        else:
            total_count = int(total_count)
    else:
        total_count = get_total_bank_auction_properties_count()

    objs = queryset.select_related('user_id').prefetch_related('property_images')[actual_offset:actual_offset + actual_page_size]
    
    data = []
    for obj in objs:
        data.append({
            'bankprop_id': obj.bankprop_id,
            'bank_name': obj.bank_name,
            'property_type': obj.property_type,
            'action_type': obj.action_type,
            'price': obj.price,
            'location': obj.location,
            'city_town': obj.city_town,
            'area_town': obj.area_town,
            'description': obj.description,
            'property_images': [{'id': img.id, 'image': img.image.name} for img in obj.property_images.all()],
            'user_first_name': obj.user_id.first_name if obj.user_id else '',
            'user_last_name': obj.user_id.last_name if obj.user_id else '',
            'user_mobile_no': obj.user_id.mobile_no if obj.user_id else '',
            'user_email': obj.user_id.email if obj.user_id else ''
        })
    return data, total_count

# --- Global Variable for total count (for faster access) ---
total_properties_count = 0
total_bank_properties_count = 0

def get_total_properties_count():
    global total_properties_count
    if total_properties_count == 0:
        total_properties_count = Property.objects.count()
    return total_properties_count

def get_total_bank_properties_count():
    global total_bank_properties_count
    if total_bank_properties_count == 0:
        total_bank_properties_count = BankAuctionProperty.objects.count()
    return total_bank_properties_count


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
        try:
            if pk:
                property_obj = Property.objects.get(pk=pk)
                serializer = PropertySerializer(property_obj)
                return Response(serializer.data)
            
            # Get pagination parameters
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            chunk = int(request.GET.get('chunk', 100))
            offset = (page - 1) * page_size
            
            # Get filtering parameters
            property_type_filter = request.GET.get('property_type', '')
            type_filter = request.GET.get('type', '')
            search_query = request.GET.get('search_query') or request.GET.get('search') or ''
            
            # Get price filters
            price_min = request.GET.get('price_min')
            price_max = request.GET.get('price_max')
            exclude_role = request.GET.get('exclude_role')
            
            # Determine cache key with price filters
            cache_key_suffix = f"_{price_min}_{price_max}_{exclude_role}"
            
            # Validate page_size
            allowed_page_sizes = [20, 50, 100, 500, 1000, 5000]
            if page_size not in allowed_page_sizes:
                page_size = 20
            
            if page_size > 100 and request.GET.get('chunk_number') is not None:
                actual_page_size = chunk
                chunk_number = int(request.GET.get('chunk_number', 0))
                actual_offset = offset + (chunk_number * chunk)
            else:
                actual_page_size = page_size
                actual_offset = offset
                chunk_number = 0

            # Determine cache key
            if search_query:
                cache_key = build_property_cache_key(search_query, property_type_filter, type_filter, page, page_size, chunk, chunk_number) + cache_key_suffix
            else:
                safe_prop_type = property_type_filter.replace(' ', '_').replace('/', '_') if property_type_filter else 'all'
                safe_type = type_filter.replace(' ', '_').replace('/', '_') if type_filter else 'all'
                if page_size > 100 and request.GET.get('chunk_number') is not None:
                    cache_key = f"property_list_{page}_{page_size}_{chunk}_{chunk_number}_{safe_prop_type}_{safe_type}" + cache_key_suffix
                else:
                    cache_key = f"property_list_{page}_{page_size}_{safe_prop_type}_{safe_type}" + cache_key_suffix

            # Try to get from cache
            cached_data = cache_manager.get(cache_key)
            if cached_data:
                try:
                    return Response(json.loads(cached_data), status=status.HTTP_200_OK)
                except (json.JSONDecodeError, TypeError):
                    pass

            if search_query:
                data, total_count = perform_meilisearch_properties(
                    search_query, property_type_filter, type_filter, actual_offset, actual_page_size,
                    price_min=price_min, price_max=price_max, exclude_role=exclude_role
                )
                if data is None:
                    data, total_count = perform_db_search_properties(
                        search_query, property_type_filter, type_filter, actual_offset, actual_page_size,
                        price_min=price_min, price_max=price_max, exclude_role=exclude_role
                    )
            else:
                # Get total count (fast)
                if property_type_filter and type_filter:
                    total_count = get_property_filter_count_fast(property_type_filter, type_filter)
                elif property_type_filter:
                    total_count = get_property_type_count_fast(property_type_filter)
                elif type_filter:
                    total_count = get_type_count_fast(type_filter)
                else:
                    total_count = get_total_properties_count_fast()
                
                # Apply MANDATORY base filters along with any optional ones
                queryset = Property.objects.filter(
                    Admin_status='Approved'
                )
                
                if exclude_role:
                    queryset = queryset.exclude(user_id__role=exclude_role)
                    
                queryset = queryset.select_related('user_id', 'category_id').only(
                    'property_id', 'property_name', 'location', 'posted_by', 'property_type', 
                    'type', 'facing', 'site_area', 'price', 'units', 'mobile_no',
                    'user_id__first_name', 'user_id__last_name', 'user_id__mobile_no', 'user_id__email',
                    'category_id__category', 'Admin_status'
                )
                
                if property_type_filter:
                    queryset = queryset.filter(property_type__iexact=property_type_filter)
                if type_filter:
                    queryset = queryset.filter(type__iexact=type_filter)
                
                # Add price filters to base query if provided without search
                if price_min is not None:
                    queryset = queryset.filter(price__gte=price_min)
                if price_max is not None:
                    queryset = queryset.filter(price__lte=price_max)
                
                # Recalculate count if price filters are applied (they aren't in the global fast counts)
                if price_min or price_max:
                    total_count = queryset.count()
                
                objs = queryset[actual_offset:actual_offset + actual_page_size]
                serializer = PropertySerializer(objs, many=True)
                data = serializer.data

            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_previous = page > 1
            
            response_data = {
                'data': data,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_previous': has_previous,
                    'next_page': page + 1 if has_next else None,
                    'previous_page': page - 1 if has_previous else None,
                }
            }
            
            # Cache the result
            try:
                response_json = json.dumps(response_data, default=str)
                cache_manager.set(cache_key, response_json, timeout=300)
            except Exception:
                pass
            
            return Response(response_data, status=status.HTTP_200_OK)

        except Property.DoesNotExist:
            return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(request=PropertySerializer)
    def post(self, request):           
        request.data['status'] = True
        serializer = PropertySerializer(data=request.data)

        if serializer.is_valid():
            property_obj = serializer.save()
            
            # Update global count
            update_total_properties_count(1)

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
            
            # Update global count
            update_total_properties_count(-1)
            
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
class PropertyRequestTypeAPIView(APIView):
    """
    API View for Property Requests filtered by looking_for type with pagination and progressive loading
    """
    
    def get(self, request):
        try:
            # Get pagination parameters
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            chunk = int(request.GET.get('chunk', 100))
            offset = (page - 1) * page_size
            
            # Get filtering parameters
            looking_for_filter = request.GET.get('looking_for', '')
            property_type_filter = request.GET.get('property_type', '')
            search_query = request.GET.get('search_query') or request.GET.get('search') or ''
            
            # Validate page_size
            allowed_page_sizes = [20, 50, 100, 500, 1000, 5000]
            if page_size not in allowed_page_sizes:
                page_size = 20
            
            if page_size > 100 and request.GET.get('chunk_number') is not None:
                actual_page_size = chunk
                chunk_number = int(request.GET.get('chunk_number', 0))
                actual_offset = offset + (chunk_number * chunk)
            else:
                actual_page_size = page_size
                actual_offset = offset
                chunk_number = 0

            # Determine cache key
            cache_key = build_wanted_property_cache_key(search_query, looking_for_filter, property_type_filter, page, page_size, chunk, chunk_number)
            
            # Try to get from cache
            cached_data = cache_manager.get(cache_key)
            if cached_data:
                try:
                    return Response(json.loads(cached_data), status=status.HTTP_200_OK)
                except (json.JSONDecodeError, TypeError):
                    pass

            if search_query:
                data, total_count = perform_meilisearch_property_requests(
                    search_query, looking_for_filter, property_type_filter, actual_offset, actual_page_size
                )
                if data is None:
                    data, total_count = perform_db_search_property_requests(
                        search_query, looking_for_filter, property_type_filter, actual_offset, actual_page_size
                    )
            else:
                # Get total count (fast)
                if looking_for_filter and property_type_filter:
                    total_count = get_looking_for_property_type_count(looking_for_filter, property_type_filter)
                elif looking_for_filter:
                    total_count = get_looking_for_count(looking_for_filter)
                elif property_type_filter:
                    total_count = get_property_type_count(property_type_filter)
                else:
                    total_count = get_total_property_requests_count()
                
                # Apply filters
                queryset = PropertyRequest.objects.all().select_related('user_id').prefetch_related('pro_loc')
                if looking_for_filter:
                    queryset = queryset.filter(looking_for__iexact=looking_for_filter)
                if property_type_filter:
                    queryset = queryset.filter(property_type__iexact=property_type_filter)
                
                objs = queryset[actual_offset:actual_offset + actual_page_size]
                
                data = []
                for obj in objs:
                    loc = obj.pro_loc.first()
                    data.append({
                        'req_id': obj.req_id,
                        'user_id': obj.user_id_id,
                        'user_first_name': obj.user_id.first_name if obj.user_id else '',
                        'user_last_name': obj.user_id.last_name if obj.user_id else '',
                        'user_mobile_no': obj.user_id.mobile_no if obj.user_id else '',
                        'user_email': obj.user_id.email if obj.user_id else '',
                        'looking_for': obj.looking_for,
                        'property_type': obj.property_type,
                        'min_budget': obj.min_budget,
                        'max_budget': obj.max_budget,
                        'no_of_bedrooms': obj.no_of_bedrooms,
                        'location': loc.location if loc else '-',
                        'area': obj.area,
                        'units': obj.units,
                        'created_at': obj.created_at,
                        'updated_at': obj.updated_at,
                    })

            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_previous = page > 1
            
            response_data = {
                'data': data,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_previous': has_previous,
                    'next_page': page + 1 if has_next else None,
                    'previous_page': page - 1 if has_previous else None,
                }
            }
            
            # Cache the result
            try:
                response_json = json.dumps(response_data, default=str)
                cache_manager.set(cache_key, response_json, timeout=300)
            except Exception:
                pass
            
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class PropertyRequestCRUD(APIView):

    
    def get(self, request, pk=None):
        try:            
            if pk:
                obj = PropertyRequest.objects.get(pk=pk)
                serializer = PropertyRequestSerializer(obj)
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            # Get pagination parameters
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            chunk = int(request.GET.get('chunk', 100))
            offset = (page - 1) * page_size
            
            # Get filtering parameters
            looking_for_filter = request.GET.get('looking_for', '')
            property_type_filter = request.GET.get('property_type', '')
            search_query = request.GET.get('search_query') or request.GET.get('search') or ''
            
            # Validate page_size
            allowed_page_sizes = [20, 50, 100, 500, 1000, 5000]
            if page_size not in allowed_page_sizes:
                page_size = 20
            
            if page_size > 100 and request.GET.get('chunk_number') is not None:
                actual_page_size = chunk
                chunk_number = int(request.GET.get('chunk_number', 0))
                actual_offset = offset + (chunk_number * chunk)
            else:
                actual_page_size = page_size
                actual_offset = offset
                chunk_number = 0

            # Determine cache key
            cache_key = build_wanted_property_cache_key(search_query, looking_for_filter, property_type_filter, page, page_size, chunk, chunk_number)
            
            # Try to get from cache
            cached_data = cache_manager.get(cache_key)
            if cached_data:
                try:
                    return Response(json.loads(cached_data), status=status.HTTP_200_OK)
                except (json.JSONDecodeError, TypeError):
                    pass

            if search_query:
                data, total_count = perform_meilisearch_property_requests(
                    search_query, looking_for_filter, property_type_filter, actual_offset, actual_page_size
                )
                if data is None:
                    data, total_count = perform_db_search_property_requests(
                        search_query, looking_for_filter, property_type_filter, actual_offset, actual_page_size
                    )
            else:
                # Get total count (fast)
                total_count = get_total_property_requests_count()
                
                # Apply filters
                queryset = PropertyRequest.objects.all().select_related('user_id').prefetch_related('pro_loc')
                if looking_for_filter:
                    queryset = queryset.filter(looking_for__iexact=looking_for_filter)
                    total_count = queryset.count()
                if property_type_filter:
                    queryset = queryset.filter(property_type__iexact=property_type_filter)
                    total_count = queryset.count()
                
                objs = queryset[actual_offset:actual_offset + actual_page_size]
                
                data = []
                for obj in objs:
                    loc = obj.pro_loc.first()
                    data.append({
                        'req_id': obj.req_id,
                        'user_id': obj.user_id_id,
                        'user_first_name': obj.user_id.first_name if obj.user_id else '',
                        'user_last_name': obj.user_id.last_name if obj.user_id else '',
                        'user_mobile_no': obj.user_id.mobile_no if obj.user_id else '',
                        'user_email': obj.user_id.email if obj.user_id else '',
                        'looking_for': obj.looking_for,
                        'property_type': obj.property_type,
                        'min_budget': obj.min_budget,
                        'max_budget': obj.max_budget,
                        'no_of_bedrooms': obj.no_of_bedrooms,
                        'location': loc.location if loc else '-',
                        'area': obj.area,
                        'units': obj.units,
                        'created_at': obj.created_at,
                        'updated_at': obj.updated_at,
                    })

            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_previous = page > 1
            
            response_data = {
                'data': data,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_previous': has_previous,
                    'next_page': page + 1 if has_next else None,
                    'previous_page': page - 1 if has_previous else None,
                }
            }
            
            # Cache the result
            try:
                response_json = json.dumps(response_data, default=str)
                cache_manager.set(cache_key, response_json, timeout=300)
            except Exception:
                pass
            
            return Response(response_data, status=status.HTTP_200_OK)

        except PropertyRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @extend_schema(request=PropertyRequestSerializer)    
    def post(self, request):
        try:
            serializer = PropertyRequestSerializer(data=request.data)
            if serializer.is_valid():

                req_rec = serializer.save()

                # Update global counts for property requests
                update_total_property_requests_count(1)
                if req_rec.looking_for:
                    update_looking_for_count(req_rec.looking_for, 1)

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
            
            # Store looking_for type before deletion for count update
            looking_for_type = obj.looking_for
            
            obj.delete()
            
            # Update global counts for property requests
            update_total_property_requests_count(-1)
            if looking_for_type:
                update_looking_for_count(looking_for_type, -1)
            
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
            
            # Get pagination parameters
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            chunk = int(request.GET.get('chunk', 100))
            offset = (page - 1) * page_size
            
            # Get filtering parameters
            property_type_filter = request.GET.get('property_type', '')
            search_query = request.GET.get('search_query') or request.GET.get('search') or ''
            
            # Validate page_size
            allowed_page_sizes = [20, 50, 100, 500, 1000, 5000]
            if page_size not in allowed_page_sizes:
                page_size = 20
            
            if page_size > 100 and request.GET.get('chunk_number') is not None:
                actual_page_size = chunk
                chunk_number = int(request.GET.get('chunk_number', 0))
                actual_offset = offset + (chunk_number * chunk)
            else:
                actual_page_size = page_size
                actual_offset = offset
                chunk_number = 0

            # Determine cache key
            if search_query:
                cache_key = build_bank_search_cache_key(search_query, property_type_filter, page, page_size, chunk, chunk_number)
            else:
                safe_type = property_type_filter.replace(' ', '_').replace('/', '_') if property_type_filter else 'all'
                if page_size > 100 and request.GET.get('chunk_number') is not None:
                    cache_key = f"bank_list_{page}_{page_size}_{chunk}_{chunk_number}_{safe_type}"
                else:
                    cache_key = f"bank_list_{page}_{page_size}_{safe_type}"

            # Try to get from cache
            cached_data = cache_manager.get(cache_key)
            if cached_data:
                try:
                    return Response(json.loads(cached_data), status=status.HTTP_200_OK)
                except (json.JSONDecodeError, TypeError):
                    pass

            if search_query:
                data, total_count = perform_meilisearch_bank_properties(
                    search_query, property_type_filter, actual_offset, actual_page_size
                )
                if data is None:
                    data, total_count = perform_db_search_bank_properties(
                        search_query, property_type_filter, actual_offset, actual_page_size
                    )
            else:
                # Get total count (fast)
                total_count = get_total_bank_auction_properties_count()
                
                # Apply type filter if provided
                queryset = BankAuctionProperty.objects.all()
                if property_type_filter:
                    queryset = queryset.filter(property_type__icontains=property_type_filter)
                    total_count = queryset.count() # Recalculate if filtered
                
                objs = queryset[actual_offset:actual_offset + actual_page_size]
                serializer = BankAuctionPropertySerializer(objs, many=True)
                data = serializer.data

            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_previous = page > 1
            
            response_data = {
                'data': data,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_previous': has_previous,
                    'next_page': page + 1 if has_next else None,
                    'previous_page': page - 1 if has_previous else None,
                }
            }
            
            # Cache the result
            try:
                response_json = json.dumps(response_data, default=str)
                cache_manager.set(cache_key, response_json, timeout=300)
            except Exception:
                pass
            
            return Response(response_data, status=status.HTTP_200_OK)

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
                # Update global count
                update_total_bank_auction_properties_count(1)
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
            # Update global count
            update_total_bank_auction_properties_count(-1)
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


from django.db.models import FloatField
from django.db.models.functions import Cast


@method_decorator(csrf_exempt, name='dispatch')
class FilteredPropertyAPIView(APIView):
    """
    Get properties with dynamic filters from payload
    Supports viewport bounds for map optimization
    """
    def post(self, request):
        try:
            include = request.data.get('include', {})
            exclude = request.data.get('exclude', {})
            
            # Map optimization parameters
            viewport_bounds = request.data.get('viewport_bounds', None)
            limit = request.data.get('limit', None)
            use_map_serializer = request.data.get('for_map', False)

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

            # Start with base queryset
            if filter_kwargs and exclude_kwargs:
                properties = Property.objects.filter(**filter_kwargs).exclude(**exclude_kwargs)
            elif filter_kwargs:
                properties = Property.objects.filter(**filter_kwargs)
            elif exclude_kwargs:
                properties = Property.objects.exclude(**exclude_kwargs)
            else:
                properties = Property.objects.all()
            
            # Ensure consistent ordering
            properties = properties.order_by('property_id')

            # Debug logging
            print(f"Filter kwargs: {filter_kwargs}")
            print(f"Exclude kwargs: {exclude_kwargs}")
            print(f"Total properties before limit: {properties.count()}")
            print(f"Limit: {limit}")

            # Apply viewport bounds filtering for map optimization
            if viewport_bounds and all(key in viewport_bounds for key in ['north', 'south', 'east', 'west']):
                try:
                    north = float(viewport_bounds['north'])
                    south = float(viewport_bounds['south'])
                    east = float(viewport_bounds['east'])
                    west = float(viewport_bounds['west'])

                    print('north', north)
                    print('south', south)
                    print('east', east)
                    print('west', west)
                    
                    # Debug logging for viewport bounds
                    print(f"Viewport bounds: North={north}, South={south}, East={east}, West={west}")
                    properties_before_bounds = properties.count()
                    print(f"Properties before bounds filtering: {properties_before_bounds}")
                    
                    # Filter properties within viewport bounds
                    # properties = properties.filter(
                    #     lat__gte=south,
                    #     lat__lte=north,
                    #     long__gte=west,
                    #     long__lte=east
                    # ).order_by('property_id')

                    properties = properties.annotate(
                        lat_float=Cast('lat', FloatField()),
                        long_float=Cast('long', FloatField())
                    ).filter(
                        lat_float__gte=south,
                        lat_float__lte=north,
                        long_float__gte=west,
                        long_float__lte=east
                    )
                    
                    print('properties', properties.first())
                    properties_after_bounds = properties.count()
                    print(f"Properties after bounds filtering: {properties_after_bounds}")
                    
                    # If no properties found in bounds, skip bounds filtering
                    if properties_after_bounds == 0 and properties_before_bounds > 0:
                        print("No properties found in viewport bounds, skipping bounds filtering")
                        # Reset to properties before bounds filtering
                        properties = Property.objects.filter(**filter_kwargs)
                        if exclude_kwargs:
                            properties = properties.exclude(**exclude_kwargs)
                        properties = properties.order_by('property_id')
                        
                except (ValueError, TypeError):
                    # If bounds are invalid, continue without bounds filtering
                    print("Invalid viewport bounds, skipping bounds filtering")
                    pass

            # Apply limit for map optimization
            if limit:
                try:
                    limit = int(limit)
                    print(f"Applying limit: {limit}")
                    properties = properties[:limit]
                    print(f"Properties after limit: {len(properties)}")
                except (ValueError, TypeError):
                    pass

            print(f"Final properties count: {len(properties)}")

            # Choose appropriate serializer
            if use_map_serializer:
                from .serializers import PropertyMapSerializer
                serializer = PropertyMapSerializer(properties, many=True)
            else:
                serializer = PropertySerializer(properties, many=True)

            return Response({
                # 'count': properties.count() if not limit else min(properties.count(), int(limit) if isinstance(limit, int) else 0),
                'count': len(properties) if limit else properties.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# @method_decorator(csrf_exempt, name='dispatch')
# class FilteredPropertyAPIView(APIView):
#     """
#     Get properties with dynamic filters from payload
#     Supports viewport-based fetching with city clustering and 20-record limit
#     """
#     def post(self, request):
#         try:
#             include = request.data.get('include', {})
#             exclude = request.data.get('exclude', {})
#             viewport_bounds = request.data.get('viewport_bounds', {})
#             zoom = request.data.get('zoom', 5)

#             # Get model fields for type checking
#             model_fields = {f.name: f for f in Property._meta.get_fields() if hasattr(f, 'name')}

#             def build_kwargs(data_dict):
#                 kwargs = {}
#                 for k, v in data_dict.items():
#                     if k in model_fields:
#                         field = model_fields[k]
#                         if isinstance(field, (models.CharField, models.TextField)):
#                             kwargs[f"{k}__iexact"] = v
#                         else:
#                             kwargs[f"{k}__exact"] = v
#                     # If field not found, skip or handle error
#                 return kwargs

#             filter_kwargs = build_kwargs(include)
#             exclude_kwargs = build_kwargs(exclude)

#             # Start with base queryset
#             if filter_kwargs and exclude_kwargs:
#                 properties = Property.objects.filter(**filter_kwargs).exclude(**exclude_kwargs)
#             elif filter_kwargs:
#                 properties = Property.objects.filter(**filter_kwargs)
#             elif exclude_kwargs:
#                 properties = Property.objects.exclude(**exclude_kwargs)
#             else:
#                 properties = Property.objects.all()

#             # Filter out properties without coordinates
#             properties = properties.exclude(lat__isnull=True).exclude(long__isnull=True)
#             properties = properties.exclude(lat='').exclude(long='')

#             # Determine zoom level and fetch accordingly
#             zoom_level = int(zoom) if zoom else 5
            
#             if zoom_level <= 8:
#                 # City-level clustering for zoomed out views
#                 return self.get_city_level_properties(properties, request)
#             else:
#                 # Individual properties with 20-record limit for zoomed in views
#                 return self.get_individual_properties(properties, viewport_bounds, request)

#         except Exception as e:
#             return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     def get_city_level_properties(self, properties, request):
#         """
#         Return city-level property clustering for zoomed out views
#         """
#         try:
#             # Apply viewport bounds if provided
#             viewport_bounds = request.data.get('viewport_bounds', {})
#             if viewport_bounds and all(key in viewport_bounds for key in ['north', 'south', 'east', 'west']):
#                 try:
#                     north = float(viewport_bounds['north'])
#                     south = float(viewport_bounds['south'])
#                     east = float(viewport_bounds['east'])
#                     west = float(viewport_bounds['west'])
                    
#                     properties = properties.annotate(
#                         lat_float=Cast('lat', FloatField()),
#                         long_float=Cast('long', FloatField())
#                     ).filter(
#                         lat_float__gte=south,
#                         lat_float__lte=north,
#                         long_float__gte=west,
#                         long_float__lte=east
#                     )
#                 except (ValueError, TypeError):
#                     pass

#             # Group by city and calculate aggregates
#             from django.db.models import Count, Avg, Min, Max, Q
            
#             city_data = []
            
#             # Extract city name from location field
#             for prop in properties:
#                 location = prop.location or ''
#                 if ',' in location:
#                     city_name = location.split(',')[0].strip()
#                 else:
#                     city_name = location.strip() or 'Unknown'
                
#                 # Find existing city entry or create new one
#                 existing_city = next((city for city in city_data if city['city_name'] == city_name), None)
                
#                 if existing_city:
#                     # Update aggregates
#                     existing_city['property_count'] += 1
#                     existing_city['properties'].append(prop)
#                     if prop.price:
#                         existing_city['total_price'] += prop.price
#                         existing_city['min_price'] = min(existing_city['min_price'], prop.price)
#                         existing_city['max_price'] = max(existing_city['max_price'], prop.price)
#                     existing_city['total_lat'] += float(prop.lat) if prop.lat else 0
#                     existing_city['total_lng'] += float(prop.long) if prop.long else 0
#                 else:
#                     # Create new city entry
#                     city_data.append({
#                         'city_name': city_name,
#                         'property_count': 1,
#                         'properties': [prop],
#                         'total_price': prop.price or 0,
#                         'min_price': prop.price or 0,
#                         'max_price': prop.price or 0,
#                         'total_lat': float(prop.lat) if prop.lat else 0,
#                         'total_lng': float(prop.long) if prop.long else 0
#                     })
            
#             # Transform city data to frontend format
#             transformed_cities = []
#             for city in city_data:
#                 if city['property_count'] > 0:
#                     avg_price = city['total_price'] / city['property_count'] if city['property_count'] > 0 else 0
#                     center_lat = city['total_lat'] / city['property_count']
#                     center_lng = city['total_lng'] / city['property_count']
                    
#                     transformed_cities.append({
#                         'id': f"city_{city['city_name'].replace(' ', '_').lower()}",
#                         'lat': center_lat,
#                         'lng': center_lng,
#                         'type': 'city_cluster',
#                         'price': round(avg_price),
#                         'area': 0,
#                         'city': city['city_name'],
#                         'locality': city['city_name'],
#                         'title': f"{city['property_count']} properties in {city['city_name']}",
#                         'bhk': 0,
#                         'status': 'city_cluster',
#                         'property_count': city['property_count'],
#                         'min_price': city['min_price'],
#                         'max_price': city['max_price'],
#                         'created_at': timezone.now().isoformat()
#                     })
            
#             # Sort by property count
#             transformed_cities.sort(key=lambda x: x['property_count'], reverse=True)
            
#             return Response({
#                 'success': True,
#                 'count': len(transformed_cities),
#                 'properties': transformed_cities,
#                 'zoom': int(request.data.get('zoom', 5)),
#                 'isCityLevel': True
#             }, status=status.HTTP_200_OK)
            
#         except Exception as e:
#             return Response({'error': f'City clustering error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     def get_individual_properties(self, properties, viewport_bounds, request):
#         """
#         Return individual properties with 20-record limit for zoomed in views
#         """
#         try:
#             # Apply viewport bounds if provided
#             if viewport_bounds and all(key in viewport_bounds for key in ['north', 'south', 'east', 'west']):
#                 try:
#                     north = float(viewport_bounds['north'])
#                     south = float(viewport_bounds['south'])
#                     east = float(viewport_bounds['east'])
#                     west = float(viewport_bounds['west'])
                    
#                     properties = properties.annotate(
#                         lat_float=Cast('lat', FloatField()),
#                         long_float=Cast('long', FloatField())
#                     ).filter(
#                         lat_float__gte=south,
#                         lat_float__lte=north,
#                         long_float__gte=west,
#                         long_float__lte=east
#                     )
#                 except (ValueError, TypeError):
#                     pass

#             # Order by creation date and limit to 20 records
#             properties = properties.order_by('-created_at')[:20]
            
#             # Transform to frontend format
#             transformed_properties = []
#             for prop in properties:
#                 transformed_properties.append({
#                     'id': prop.property_id,
#                     'lat': float(prop.lat) if prop.lat else 0,
#                     'lng': float(prop.long) if prop.long else 0,
#                     'type': prop.property_type or 'apartment',
#                     'price': prop.price or 0,
#                     'area': prop.buildup_area or 1000,
#                     'city': prop.location.split(',')[0] if prop.location and ',' in prop.location else (prop.location or 'India'),
#                     'locality': prop.nearby or (prop.location.split(',')[0] if prop.location and ',' in prop.location else prop.location or 'Location'),
#                     'title': prop.property_name or f"{prop.property_type or 'Property'} in {prop.nearby or 'City'}",
#                     'bhk': prop.bedrooms_count or 2,
#                     'status': 'ready',
#                     'created_at': prop.created_at.isoformat() if prop.created_at else timezone.now().isoformat()
#                 })
            
#             return Response({
#                 'success': True,
#                 'count': len(transformed_properties),
#                 'properties': transformed_properties,
#                 'zoom': int(request.data.get('zoom', 5)),
#                 'isCityLevel': False
#             }, status=status.HTTP_200_OK)
            
#         except Exception as e:
#             return Response({'error': f'Individual properties error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@method_decorator(csrf_exempt, name='dispatch')
class FilteredListPropertyAPIView(APIView):
    """
    Get properties with dynamic filters from payload
    Supports offset and limit for infinite scrolling with caching
    """
    def post(self, request):
        try:
            include = request.data.get('include', {})
            exclude = request.data.get('exclude', {})
            offset = request.data.get('offset', 0)
            limit = request.data.get('limit', 10)

            # Convert offset and limit to integers
            try:
                offset = int(offset)
                limit = int(limit)
            except (ValueError, TypeError):
                offset = 0
                limit = 10

            # Create cache key based on filters and pagination
            # Sanitize filter parameters for cache key
            def sanitize_for_cache(data_dict):
                sanitized = {}
                for k, v in data_dict.items():
                    if v is not None:
                        # Replace spaces and special characters with underscores
                        safe_key = k.replace(' ', '_').replace('/', '_').replace('%', '_')
                        safe_value = str(v).replace(' ', '_').replace('/', '_').replace('%', '_')
                        sanitized[safe_key] = safe_value
                return sanitized

            safe_include = sanitize_for_cache(include)
            safe_exclude = sanitize_for_cache(exclude)
            print('safe_include', safe_include)
            print('safe_exclude', safe_exclude)
            # Build cache key
            include_str = '_'.join([f"{k}_{v}" for k, v in sorted(safe_include.items())])
            exclude_str = '_'.join([f"{k}_{v}" for k, v in sorted(safe_exclude.items())])
            cache_key = f"properties_list_{offset}_{limit}_{include_str}_{exclude_str}"
            
            # Try to get from cache first using cache manager
            cached_data = cache_manager.get(cache_key)
            if cached_data:
                try:
                    return Response(json.loads(cached_data), status=status.HTTP_200_OK)
                except (json.JSONDecodeError, TypeError):
                    pass  # Invalid cache data, continue with database query

            # Get model fields for type checking
            model_fields = {f.name: f for f in Property._meta.get_fields() if hasattr(f, 'name')}

            def build_kwargs(data_dict):
                kwargs = {}
                for k, v in data_dict.items():
                    # Handle Django lookup expressions (like price__gte, price__lte)
                    if '__' in k:
                        field_name = k.split('__')[0]
                        lookup_expr = '__' + '__'.join(k.split('__')[1:])
                        
                        if field_name in model_fields:
                            field = model_fields[field_name]
                            # For text fields, use iexact for exact matches, but preserve other lookups
                            if lookup_expr == '__exact' and isinstance(field, (models.CharField, models.TextField)):
                                kwargs[f"{field_name}__iexact"] = v
                            else:
                                kwargs[k] = v  # Keep the original lookup expression
                        else:
                            kwargs[k] = v  # Keep the original if field not found
                    else:
                        # Handle regular field names
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

            # Start with base queryset
            if filter_kwargs and exclude_kwargs:
                properties = Property.objects.filter(**filter_kwargs).exclude(**exclude_kwargs)
            elif filter_kwargs:
                properties = Property.objects.filter(**filter_kwargs)
            elif exclude_kwargs:
                properties = Property.objects.exclude(**exclude_kwargs)
            else:
                properties = Property.objects.all()
            
            # Get total count before pagination
            total_count = properties.count()
            
            # Apply pagination
            properties = properties[offset:offset + limit]

            serializer = PropertyMapSerializer(properties, many=True)

            response_data = {
                'count': total_count,
                'offset': offset,
                'limit': limit,
                'has_more': offset + limit < total_count,
                'data': serializer.data
            }

            # Try to cache the result using cache manager
            try:
                response_json = json.dumps(response_data, default=str)
                cache_manager.set(cache_key, response_json, timeout=300)  # Cache for 5 minutes
            except Exception:
                pass  # Cache not available, continue

            return Response(response_data, status=status.HTTP_200_OK)
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
            )[:10]
            serializer = SellPropertySummarySerializer(properties, many=True)
            return Response({
                'count': properties.count(),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

