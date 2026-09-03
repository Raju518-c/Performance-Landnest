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

    # path(
    #     "ad-property/",
    #     AdPropertyAPIView.as_view(),
    #     name="ad-property-list-create"
    # ),

    # path(
    #     "ad-property/<int:pk>/",
    #     AdPropertyAPIView.as_view(),
    #     name="ad-property-detail"
    # ),



    # ========================================================
    # MAIN PROPERTY
    # ========================================================

    path(
        "ad-properties/",
        AdPropertyAPIView.as_view(),
        name="ad-properties"
    ),

    path(
        "ad-properties/<int:pk>/",
        AdPropertyAPIView.as_view(),
        name="ad-property-detail"
    ),


    # ========================================================
    # HERO IMAGES
    # ========================================================

    path(
        "ad-properties/<int:property_id>/hero-images/",
        AdProperty_imagesAPIView.as_view(),
        name="ad-property-hero-images"
    ),

    path(
        "ad-property-hero-images/<int:pk>/",
        AdProperty_imagesDetailAPIView.as_view(),
        name="ad-property-hero-image-detail"
    ),


    # ========================================================
    # BUILDER
    # ========================================================

    path(
        "ad-properties/<int:property_id>/builder-details/",
        AdPropertyBuilderDetailsAPIView.as_view(),
        name="ad-property-builder-details"
    ),


    # ========================================================
    # CONFIGURATIONS
    # ========================================================

    path(
        "ad-properties/<int:property_id>/configurations/",
        AdPropertyConfigurationAPIView.as_view(),
        name="ad-property-configurations"
    ),

    path(
        "ad-property-configurations/<int:pk>/",
        AdPropertyConfigurationDetailAPIView.as_view(),
        name="ad-property-configuration-detail"
    ),


    # ========================================================
    # FLOOR PLANS
    # ========================================================

    path(
        "ad-property-configurations/<int:configuration_id>/floor-plans/",
        AdPropertyFloorPlanImageAPIView.as_view(),
        name="ad-property-floor-plans"
    ),

    path(
        "ad-property-floor-plans/<int:pk>/",
        AdPropertyFloorPlanImageDetailAPIView.as_view(),
        name="ad-property-floor-plan-detail"
    ),


    # ========================================================
    # LOCATION ADVANTAGES
    # ========================================================

    path(
        "ad-properties/<int:property_id>/location-advantages/",
        AdPropertyLocationAdvantageAPIView.as_view(),
        name="ad-property-location-advantages"
    ),

    path(
        "ad-property-location-advantages/<int:pk>/",
        AdPropertyLocationAdvantageDetailAPIView.as_view(),
        name="ad-property-location-advantage-detail"
    ),


    # ========================================================
    # HIGHLIGHTS
    # ========================================================

    path(
        "ad-properties/<int:property_id>/highlights/",
        AdPropertyHighlightAPIView.as_view(),
        name="ad-property-highlights"
    ),

    path(
        "ad-property-highlights/<int:pk>/",
        AdPropertyHighlightDetailAPIView.as_view(),
        name="ad-property-highlight-detail"
    ),


    # ========================================================
    # AMENITIES
    # ========================================================

    path(
        "ad-properties/<int:property_id>/amenities/",
        AdPropertyAmenityAPIView.as_view(),
        name="ad-property-amenities"
    ),

    path(
        "ad-property-amenities/<int:pk>/",
        AdPropertyAmenityDetailAPIView.as_view(),
        name="ad-property-amenity-detail"
    ),


    # ========================================================
    # SPECIFICATIONS
    # ========================================================

    path(
        "ad-properties/<int:property_id>/specifications/",
        AdPropertySpecificationAPIView.as_view(),
        name="ad-property-specifications"
    ),

    path(
        "ad-property-specifications/<int:pk>/",
        AdPropertySpecificationDetailAPIView.as_view(),
        name="ad-property-specification-detail"
    ),


    # ========================================================
    # BROCHURES
    # ========================================================

    path(
        "ad-properties/<int:property_id>/brochures/",
        AdPropertyBrochureAPIView.as_view(),
        name="ad-property-brochures"
    ),

    path(
        "ad-property-brochures/<int:pk>/",
        AdPropertyBrochureDetailAPIView.as_view(),
        name="ad-property-brochure-detail"
    ),


    # ========================================================
    # COMBINED
    # ========================================================

    path(
        "ad-properties/combined/",
        AdPropertyCombinedAPIView.as_view(),
        name="ad-property-combined"
    ),

    path(
        "ad-properties/combined/<int:pk>/",
        AdPropertyCombinedDetailAPIView.as_view(),
        name="ad-property-combined-detail"
    ),
            

]
    

