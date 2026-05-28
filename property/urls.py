from django.urls import path
from .views import *
from .filter_fetch_views import *

urlpatterns = [   
    path('property-category/', PropertyCatView.as_view()),         
    path('property-category/<int:pk>/', PropertyCatView.as_view()),
    path('property/', PropertyAPIView.as_view()),         
    path('property/<int:pk>/', PropertyAPIView.as_view()),

    path('get-property/<str:user_id>/', GetUserProperty.as_view()),
    path('get-property/<str:user_id>/<str:type>/', GetPropertyType.as_view()),
    path('properties-update/', BulkPropertyUpdateAPIView.as_view()),

    path('boost-property/', BoostPropertyAPIView.as_view(), name='boost-property'),


    path('property-request/', PropertyRequestCRUD.as_view()),          # POST, GET ALL
    path('property-request/<int:pk>/', PropertyRequestCRUD.as_view()), # GET, PUT, DELETE
    path('property-request/type/', PropertyRequestTypeAPIView.as_view()), # GET by looking_for type
    
    path('response-property-request/', ResponsePropertyRequestCRUD.as_view()),
    path('response-property-request/<int:pk>/', ResponsePropertyRequestCRUD.as_view()),

    path('auction-property/', BankAuctionPropertyView.as_view()),
    path('auction-property/<int:pk>/', BankAuctionPropertyView.as_view()),

    path('properties/lease/', LeasePropertyListAPIView.as_view(), name='lease-properties'),

    path('properties/sell/admin/', SellPropertiesByAdminAPIView.as_view(), name='sell-properties-admin'),
    path('properties/sell/non-admin/', SellPropertiesByNonAdminAPIView.as_view(), name='sell-properties-non-admin'),
    path('properties/sell/non-admin/coordinates/', SellPropertiesByNonAdminCoordinatesAPIView.as_view(), name='sell-properties-non-admin-coordinates'),
    path('properties/sell/non-admin/summary/<int:pk>/', SellPropertiesByNonAdminSummaryAPIView.as_view(), name='sell-properties-non-admin-summary'),
    path('properties/best-deal/approved/', BestDealApprovedPropertiesAPIView.as_view(), name='best-deal-approved'),
    
    path('properties/filter/', FilteredPropertyAPIView.as_view(), name='filtered-properties'),

    path('properties/list_filter/', FilteredListPropertyAPIView.as_view(), name='filtered-list-properties'),

    path('bank-properties/filter/', FilteredBankAuctionPropertyAPIView.as_view(), name='filtered-bank-auction-properties'),

    path('properties/sell/non-admin/box/', SellPropertiesByNonAdminboxAPIView.as_view()),
    path('dynamic/table/filter/', MultiModelDynamicAPIView.as_view()),
]
