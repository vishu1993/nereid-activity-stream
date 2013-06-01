# -*- coding: utf-8 -*-
"""
    activity_stream

    Activity Stream module.

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool
from trytond.exceptions import UserError

from nereid import request, url_for, jsonify


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
    score = fields.Function(
        fields.Integer('Score'), 'get_score'
    )


    def __init__(self):
        super(Activity, self).__init__()
        self._order = [('create_date', 'DESC')]

    def get_score(self, ids, name):
        """
        Returns an integer score which could be used for sorting the activities
        by external system like caches, which may not be able to sort on the
        date.

        This score is based on the create date of the activity.

        :param ids: list of id.
        :param name: name of field.

        :return: Dictonary with updated values.
        """
        res = {}
        for activity in self.browse(ids):
            res[activity.id] = int(activity.create_date.strftime('%s'))
        return res

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
        nereid_user_obj = Pool().get('nereid.user')

        if not self.search([('id', '=', activity.id)], count=True):
            return None

        if not activity.object_:
            # When the object_ which caused the activity is no more
            # the value will be False
            return None

        response_json = {
            "published": activity.create_date.isoformat(),
            "actor": nereid_user_obj._json(activity.actor),
            "verb": activity.verb,
        }

        # Split the reference field data and get a browse record
        # for it.
        object_model = activity.object_.split(',')[0]
        object_obj = Pool().get(object_model)
        object_id = int(activity.object_.split(',')[1])

        object_ = object_obj.browse(object_id)
        try:
            object_.rec_name
        except UserError:
            # The record may not exist anymore which results in
            # a read error
            return None
        else:
            response_json["object"] = object_obj._json(object_)

        if activity.target:
            # Split the reference field data and get a browse record
            # for it.
            target_model = activity.target.split(',')[0]
            target_id = int(activity.target.split(',')[1])

            target = Pool().get(target_model).browse(target_id)
            response_json["target"] = target._json(target)

        return response_json

    def get_activity_stream_domain(self):
        '''Returns the domain to get activity stream
        '''
        return []

    def stream(self):
        '''Return JSON Serialized Activity Stream to XHR.
        As defined by the activity stream json specification 1.0
        http://activitystrea.ms/specs/json/1.0/
        '''
        offset = request.args.get('offset', 0, int)
        limit = request.args.get('limit', 100, int)

        ids = self.search(
            self.get_activity_stream_domain(),
            limit=limit, offset=offset,
        )

        items = filter(
            None, map(lambda x: self.serialize(x), self.browse(ids))
        )

        return jsonify({
            'totalItems': len(items),
            'items': items,
        })

Activity()


class ActivityAllowedModel(ModelSQL, ModelView):
    '''
    Nereid activity allowed model

    The model stores name (name) and model (ir.model) as list of allowed model
    in activty.
    '''
    _name = 'nereid.activity.allowed_model'
    _description = __doc__.split('\n')[0]

    name = fields.Char("Name", required=True, select=True)
    model = fields.Many2One('ir.model', 'Model', required=True, select=True)

    def __init__(self):
        super(ActivityAllowedModel, self).__init__()
        self._sql_constraints += [
            ('unique_model', 'UNIQUE(model)',
                'Name is already used.'),
            ('unique_name', 'UNIQUE(name)',
                'Model is already used.'),
            ]

ActivityAllowedModel()


class NereidUser(ModelSQL, ModelView):
    '''
    Nereid User
    '''
    _name = 'nereid.user'

    def _json(self, actor):
        """
        Serialize the actor alone and return a dictionary. This is separated
        so that other modules can easily modify the behavior independent of
        this modules.

        :param actor: Browse record of nereid.user.
        """
        return {
            "url": None,
            "objectType": self._name,
            "id": actor.id,
            "displayName": actor.display_name,
        }

NereidUser()
