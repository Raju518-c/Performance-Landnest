import os
import re
import sys
from functools import lru_cache
import django
from django.apps import apps
from django.conf import settings
try:
    import meilisearch
except ImportError:
    meilisearch = None

MEILISEARCH_INDEX_NAME = 'users'
MEILISEARCH_SEARCHABLE_ATTRIBUTES = [
    'first_name', 'last_name', 'email', 'mobile_no', 'state', 'city', 'user_type'
]
MEILISEARCH_DISPLAYED_ATTRIBUTES = [
    'user_id', 'username', 'first_name', 'last_name', 'email', 'mobile_no',
    'state', 'city', 'role', 'user_type', 'created_at', 'updated_at'
]
MEILISEARCH_FILTERABLE_ATTRIBUTES = ['role', 'user_type']

# Bank Auction Property constants
MEILI_BANK_INDEX = 'bank_auction_properties'
MEILI_BANK_SEARCHABLE = [
    'bank_name', 'property_type', 'action_type', 'location', 'city_town', 
    'area_town', 'area', 'emd_amount', 'bid_increment', 
    'auction_start_datetime', 'auction_end_datetime'
]
MEILI_BANK_DISPLAYED = [
    'bankprop_id', 'auction_id', 'bank_name', 'property_type', 'action_type',
    'location', 'city_town', 'area_town', 'lat', 'long', 'area', 'units',
    'possession', 'reserve_price', 'possession_status', 'emd_amount',
    'bid_increment', 'emd_submission', 'auction_start_datetime', 
    'auction_end_datetime', 'bank_contact_details', 'description', 
    'status', 'created_at', 'updated_at', 'user_id'
]
MEILI_BANK_FILTERABLE = ['status', 'property_type', 'bank_name', 'city_town']

# Property constants
MEILI_PROPERTY_INDEX = 'properties'
MEILI_PROPERTY_SEARCHABLE = [
    'property_name', 'location', 'posted_by', 'description', 'property_type', 
    'type', 'category_name', 'first_name', 'last_name', 'facing', 'units',
    'min_budget', 'max_budget', 'min_acres', 'max_acres', 'price',
    '_1bhk_count', '_2bhk_count', '_3bhk_count', '_4bhk_count', 
    'rooms_count', 'bedrooms_count', 'no_of_flores', 'lift'
]
MEILI_PROPERTY_DISPLAYED = [
    'property_id', 'user_id', 'property_name', 'location', 'posted_by', 
    'description', 'property_type', 'type', 'category_id', 'category_name', 
    'price', 'site_area', 'facing', 'units', 'min_budget', 'max_budget', 
    'min_acres', 'max_acres', '_1bhk_count', '_2bhk_count', '_3bhk_count', 
    '_4bhk_count', 'rooms_count', 'bedrooms_count', 'no_of_flores', 'lift',
    'first_name', 'last_name', 'mobile_no', 'email', 'created_at', 'updated_at', 'Admin_status', 'user_role'
]
MEILI_PROPERTY_FILTERABLE = ['type', 'Admin_status', 'category_name', 'property_type', 'user_id', 'price', 'user_role']

# Wanted Property (Property Request) constants
MEILI_WANTED_INDEX = 'property_requests'
MEILI_WANTED_SEARCHABLE = [
    'first_name', 'last_name', 'looking_for', 'property_type', 
    'min_budget', 'max_budget', 'no_of_bedrooms', 'location'
]
MEILI_WANTED_DISPLAYED = [
    'req_id', 'user_id', 'first_name', 'last_name', 'user_mobile_no', 'user_email',
    'looking_for', 'property_type', 'min_budget', 'max_budget', 'no_of_bedrooms',
    'location', 'area', 'units', 'created_at', 'updated_at'
]
MEILI_WANTED_FILTERABLE = ['looking_for', 'property_type', 'user_id']


@lru_cache(maxsize=1)
def get_meilisearch_client():
    if meilisearch is None:
        return None
    meili_url = getattr(settings, 'MEILISEARCH_URL', os.environ.get('MEILISEARCH_URL', 'http://127.0.0.1:7700'))
    meili_api_key = getattr(settings, 'MEILISEARCH_API_KEY', os.environ.get('MEILISEARCH_API_KEY', None))
    if meili_api_key:
        return meilisearch.Client(meili_url, meili_api_key)
    return meilisearch.Client(meili_url)


@lru_cache(maxsize=1)
def get_meilisearch_user_index():
    try:
        client = get_meilisearch_client()
        try:
            index = client.get_index(MEILISEARCH_INDEX_NAME)
        except Exception:
            index = client.create_index(MEILISEARCH_INDEX_NAME, {'primaryKey': 'user_id'})

        try:
            index.update_searchable_attributes(MEILISEARCH_SEARCHABLE_ATTRIBUTES)
            index.update_displayed_attributes(MEILISEARCH_DISPLAYED_ATTRIBUTES)
            index.update_filterable_attributes(MEILISEARCH_FILTERABLE_ATTRIBUTES)
            index.update_ranking_rules(['typo', 'words', 'proximity', 'attribute', 'exactness'])
            index.update_pagination({'maxTotalHits': 100000})
        except Exception:
            pass

        try:
            stats = index.get_stats()
            if stats.get('numberOfDocuments', 0) == 0:
                User = apps.get_model('users', 'User')
                users = list(
                    User.objects.filter(role='1').values(*MEILISEARCH_DISPLAYED_ATTRIBUTES)
                )
                if users:
                    index.add_documents(users)
        except Exception:
            pass

        return index
    except Exception:
        return None


@lru_cache(maxsize=1)
def get_meilisearch_property_index():
    try:
        client = get_meilisearch_client()
        try:
            index = client.get_index(MEILI_PROPERTY_INDEX)
        except Exception:
            index = client.create_index(MEILI_PROPERTY_INDEX, {'primaryKey': 'property_id'})

        try:
            index.update_searchable_attributes(MEILI_PROPERTY_SEARCHABLE)
            index.update_displayed_attributes(MEILI_PROPERTY_DISPLAYED)
            index.update_filterable_attributes(MEILI_PROPERTY_FILTERABLE)
            index.update_ranking_rules(['typo', 'words', 'proximity', 'attribute', 'exactness'])
            index.update_pagination({'maxTotalHits': 100000})
        except Exception:
            pass

        return index
    except Exception:
        return None


def format_property_for_index(prop):
    user = prop.user_id
    category = prop.category_id
    print('prop.Admin_status', prop.Admin_status)
    return {
        'property_id': prop.property_id,
        'user_id': prop.user_id_id,
        'first_name': user.first_name if user else None,
        'last_name': user.last_name if user else None,
        'mobile_no': user.mobile_no if user else None,
        'email': user.email if user else None,
        'property_name': prop.property_name,
        'location': prop.location,
        'posted_by': prop.posted_by,
        'description': prop.description,
        'property_type': prop.property_type,
        'type': prop.type,
        'category_id': prop.category_id_id,
        'category_name': category.category if category else None,
        'price': prop.price,
        'site_area': prop.site_area,
        'facing': prop.facing,
        'units': prop.units,
        'min_budget': prop.min_budget,
        'max_budget': prop.max_budget,
        'min_acres': prop.min_acres,
        'max_acres': prop.max_acres,
        '_1bhk_count': prop._1bhk_count,
        '_2bhk_count': prop._2bhk_count,
        '_3bhk_count': prop._3bhk_count,
        '_4bhk_count': prop._4bhk_count,
        'rooms_count': prop.rooms_count,
        'bedrooms_count': prop.bedrooms_count,
        'no_of_flores': prop.no_of_flores,
        'lift': prop.lift,
        'Admin_status': prop.Admin_status,
        'user_role': user.role if user else None,
        'created_at': prop.created_at.isoformat() if prop.created_at else None,
        'updated_at': prop.updated_at.isoformat() if prop.updated_at else None,
    }


def add_or_update_property_in_meilisearch(prop):
    index = get_meilisearch_property_index()
    if not index:
        return

    document = format_property_for_index(prop)
    try:
        index.add_documents([document])
    except Exception:
        pass


def remove_property_from_meilisearch(property_id):
    index = get_meilisearch_property_index()
    if not index:
        return

    try:
        index.delete_document(property_id)
    except Exception:
        pass


@lru_cache(maxsize=1)
def get_meilisearch_wanted_index():
    try:
        client = get_meilisearch_client()
        try:
            index = client.get_index(MEILI_WANTED_INDEX)
        except Exception:
            index = client.create_index(MEILI_WANTED_INDEX, {'primaryKey': 'req_id'})

        try:
            index.update_searchable_attributes(MEILI_WANTED_SEARCHABLE)
            index.update_displayed_attributes(MEILI_WANTED_DISPLAYED)
            index.update_filterable_attributes(MEILI_WANTED_FILTERABLE)
            index.update_ranking_rules(['typo', 'words', 'proximity', 'attribute', 'exactness'])
            index.update_pagination({'maxTotalHits': 100000})
        except Exception:
            pass

        return index
    except Exception:
        return None


def format_wanted_property_for_index(req):
    user = req.user_id
    # Get first location if exists
    loc = req.pro_loc.first()
    return {
        'req_id': req.req_id,
        'user_id': req.user_id_id,
        'first_name': user.first_name if user else None,
        'last_name': user.last_name if user else None,
        'user_mobile_no': user.mobile_no if user else None,
        'user_email': user.email if user else None,
        'looking_for': req.looking_for,
        'property_type': req.property_type,
        'min_budget': req.min_budget,
        'max_budget': req.max_budget,
        'no_of_bedrooms': req.no_of_bedrooms,
        'location': loc.location if loc else None,
        'area': req.area,
        'units': req.units,
        'created_at': req.created_at.isoformat() if req.created_at else None,
        'updated_at': req.updated_at.isoformat() if req.updated_at else None,
    }


def add_or_update_wanted_property_in_meilisearch(req):
    index = get_meilisearch_wanted_index()
    if not index:
        return

    document = format_wanted_property_for_index(req)
    try:
        index.add_documents([document])
    except Exception:
        pass


def remove_wanted_property_from_meilisearch(req_id):
    index = get_meilisearch_wanted_index()
    if not index:
        return

    try:
        index.delete_document(req_id)
    except Exception:
        pass


@lru_cache(maxsize=1)
def get_meilisearch_bank_index():
    try:
        client = get_meilisearch_client()
        try:
            index = client.get_index(MEILI_BANK_INDEX)
        except Exception:
            index = client.create_index(MEILI_BANK_INDEX, {'primaryKey': 'bankprop_id'})

        try:
            index.update_searchable_attributes(MEILI_BANK_SEARCHABLE)
            index.update_displayed_attributes(MEILI_BANK_DISPLAYED)
            index.update_filterable_attributes(MEILI_BANK_FILTERABLE)
            index.update_ranking_rules(['typo', 'words', 'proximity', 'attribute', 'exactness'])
            index.update_pagination({'maxTotalHits': 100000})
        except Exception:
            pass

        return index
    except Exception:
        return None


def format_bank_property_for_index(prop):
    return {
        'bankprop_id': prop.bankprop_id,
        'auction_id': prop.auction_id,
        'bank_name': prop.bank_name,
        'property_type': prop.property_type,
        'action_type': prop.action_type,
        'location': prop.location,
        'city_town': prop.city_town,
        'area_town': prop.area_town,
        'lat': prop.lat,
        'long': prop.long,
        'area': prop.area,
        'units': prop.units,
        'possession': prop.possession,
        'reserve_price': prop.reserve_price,
        'possession_status': prop.possession_status,
        'emd_amount': prop.emd_amount,
        'bid_increment': prop.bid_increment,
        'emd_submission': prop.emd_submission.isoformat() if prop.emd_submission else None,
        'auction_start_datetime': prop.auction_start_datetime.isoformat() if prop.auction_start_datetime else None,
        'auction_end_datetime': prop.auction_end_datetime.isoformat() if prop.auction_end_datetime else None,
        'bank_contact_details': prop.bank_contact_details,
        'description': prop.description,
        'status': prop.status,
        'created_at': prop.created_at.isoformat() if prop.created_at else None,
        'updated_at': prop.updated_at.isoformat() if prop.updated_at else None,
        'user_id': prop.user_id_id if prop.user_id else None,
    }


def add_or_update_bank_property_in_meilisearch(prop):
    index = get_meilisearch_bank_index()
    if not index:
        return

    document = format_bank_property_for_index(prop)
    try:
        index.add_documents([document])
    except Exception:
        pass


def remove_bank_property_from_meilisearch(bankprop_id):
    index = get_meilisearch_bank_index()
    if not index:
        return

    try:
        index.delete_document(bankprop_id)
    except Exception:
        pass


def format_user_for_index(user):
    return {
        'user_id': user.user_id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'mobile_no': user.mobile_no,
        'state': user.state,
        'city': user.city,
        'role': user.role,
        'user_type': user.user_type,
        'created_at': user.created_at,
        'updated_at': user.updated_at,
    }


def add_or_update_user_in_meilisearch(user):
    index = get_meilisearch_user_index()
    if not index:
        return

    if user.role != '1':
        try:
            index.delete_document(user.user_id)
        except Exception:
            pass
        return

    document = format_user_for_index(user)
    try:
        index.add_documents([document])
    except Exception:
        pass


def remove_user_from_meilisearch(user_id):
    index = get_meilisearch_user_index()
    if not index:
        return

    try:
        index.delete_document(user_id)
    except Exception:
        pass


if __name__ == '__main__':
    root_dir = os.path.abspath(os.path.dirname(__file__))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'landnest.settings')
    django.setup()

    print('Initializing Meilisearch index...')
    index = get_meilisearch_user_index()
    if index:
        try:
            stats = index.get_stats()
            print(f"Meilisearch index '{MEILISEARCH_INDEX_NAME}' ready")
            print(f"Document count: {stats.get('numberOfDocuments', 'unknown')}")
        except Exception:
            print(f"Meilisearch index '{MEILISEARCH_INDEX_NAME}' ready, but stats unavailable")
    else:
        print('Failed to initialize Meilisearch index. Check MEILISEARCH_URL/MEILISEARCH_API_KEY and Django settings.')
