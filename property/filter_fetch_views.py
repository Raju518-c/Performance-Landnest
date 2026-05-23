from django.apps import apps
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import *
from landnest_admin.models import *
from users.models import *



class MultiModelDynamicAPIView(APIView):   

    ALLOWED_APPS = [
        'property',
        'landnest_admin',
        'users'
    ]

    def get_allowed_models(self):
        allowed_models = {}

        for app_label in self.ALLOWED_APPS:
            app_models = apps.get_app_config(app_label).get_models()

            for model in app_models:
                allowed_models[model.__name__] = model

        return allowed_models 

    RELATED_MODELS = {
        "Property": {
            "property_images": {
                "model": "PropertyImages",
                "fk": "property_id"
            }
        }
    }

    def get_model(self, model_name):
        allowed_models = self.get_allowed_models()
        return allowed_models.get(model_name)

    def build_kwargs(self, model, data_dict):
        model_fields = {f.name: f for f in model._meta.get_fields() if hasattr(f, 'name')}
        kwargs = {}

        for k, v in data_dict.items():
            if k in model_fields:
                field = model_fields[k]

                if isinstance(field, (models.CharField, models.TextField)):
                    kwargs[f"{k}__iexact"] = v
                else:
                    kwargs[f"{k}__exact"] = v

        return kwargs

    def post(self, request):
        try:
            queries = request.data.get('queries', [])
            final_response = {}

            for query in queries:
                model_name = query.get("model")

                if model_name not in self.ALLOWED_MODELS:
                    continue

                model = self.get_model(model_name)
                if not model:
                    continue

                include = query.get("include", {})
                exclude = query.get("exclude", {})
                fields = query.get("fields", [])
                related = query.get("related", {})

                queryset = model.objects.all()

                filter_kwargs = self.build_kwargs(model, include)
                exclude_kwargs = self.build_kwargs(model, exclude)

                if filter_kwargs:
                    queryset = queryset.filter(**filter_kwargs)

                if exclude_kwargs:
                    queryset = queryset.exclude(**exclude_kwargs)

                data = list(queryset.values(*fields)) if fields else list(queryset.values())

                # 🔥 HANDLE RELATED DATA
                if related and model_name in self.RELATED_MODELS:
                    for rel_key, rel_config in related.items():

                        rel_info = self.RELATED_MODELS[model_name].get(rel_key)
                        if not rel_info:
                            continue

                        rel_model = self.get_model(rel_info["model"])
                        fk_field = rel_info["fk"]

                        rel_fields = rel_config.get("fields", [])
                        limit = rel_config.get("limit", None)

                        for row in data:
                            parent_id = row.get("property_id")

                            rel_qs = rel_model.objects.filter(**{fk_field: parent_id})

                            if limit:
                                rel_qs = rel_qs[:limit]

                            if rel_fields:
                                rel_qs = rel_qs.values(*rel_fields)
                            else:
                                rel_qs = rel_qs.values()

                            row[rel_key] = list(rel_qs)

                final_response[model_name] = {
                    "count": len(data),
                    "data": data
                }

            return Response(final_response, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)