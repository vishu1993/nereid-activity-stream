# -*- coding: utf-8 -*-
"""
    activity_stream

    Activity Stream module.

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool

from nereid import url_for


class NereidUser(ModelSQL, ModelView):
    "Nereid User"
    _name = 'nereid.user'

    activities = fields.One2Many(
        'nereid.activity', 'actor', 'Activities'
    )

NereidUser()


class Activity(ModelSQL, ModelView):
    '''Nereid user activity

    The model stores activities (verb) performed by nereid users (actor). The
    field names and data structure is inspired by the activity stream json
    specification 1.0 http://activitystrea.ms/specs/json/1.0/
    '''
    _name = 'nereid.activity'
    _description = __doc__.split('\n')[0]

    actor = fields.Many2One(
        'nereid.user', 'Actor', required=True, select=True
    )
    verb = fields.Char("Verb", required=True, select=True)
    object_ = fields.Reference(
        "Object", selection='models_get', select=True, required=True,
    )
    target = fields.Reference(
        "Target", selection='models_get', select=True,
    )

    def models_get(self):
        '''Return valid models where activity stream could have valid objects
        and targets.
        '''
        allowed_model_obj = Pool().get('nereid.activity.allowed_model')

        allowed_model_ids = allowed_model_obj.search([])
        res = []
        for allowed_model in allowed_model_obj.browse(allowed_model_ids):
            res.append((allowed_model.model.model, allowed_model.name))
        return res

    def serialize(self, activity):
        '''Return a JSON Seralizable dictionary that could be stored in a
        cache and sent by XHR.

        If additional information needs to be passed with the serialized data,
        a subclass could get the returned dictionary and inject properties
        anywhere in the dictionary (to be JSON object). This is respected by
        the JSON Activity Streams 1.0 spec.

        :param activity: Browse record of activity
        '''
        json = {
            "published": str(activity.create_date),
            "actor": {
                "url": url_for(
                    'nereid.user.user_profile',
                    username=activity.actor.username
                ),
                "objectType": "nereid.user",
                "id": activity.actor.id,
                "image": {
                    "url": activity.actor.get_profile_picture(
                        activity.actor,
                        size=50, https=True
                    ),
                    "width": 50,
                    "height": 50,
                },
                "displayName": activity.actor.display_name,
            },
            "verb": activity.verb,
            "object": {
                "url": activity.object_.url,
                "id": activity.object_.id,
                "objectType": activity.object_.model.model,
                "displayName": activity.object_.rec_name,
            },
        }
        if activity.target:
            json["target"] = {
                "url": activity.target.url,
                "objectType": activity.object_.model.model,
                "id": activity.target.id,
                "displayName": activity.target.rec_name,
            }

        return json

Activity()


class ActivityAllowedModel(ModelSQL, ModelView):
    '''Nereid activity allowed model

    The model stores name (name) and model (ir.model) as list of allowed model
    in activty.
    '''
    _name = 'nereid.activity.allowed_model'
    _description = __doc__.split('\n')[0]

    name = fields.Char("Name", required=True, select=True)
    model = fields.Many2One('ir.model', 'Model', required=True, select=True)

ActivityAllowedModel()
