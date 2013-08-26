# -*- coding: utf-8 -*-
"""
    activity_stream

    Activity Stream module.

    :copyright: (c) 2013 by Openlabs Technologies & Consulting (P) Limited
    :license: GPLv3, see LICENSE for more details.
"""
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.exceptions import UserError

from nereid import request, jsonify

__all__ = ['NereidUser', 'Activity', 'ActivityAllowedModel']
__metaclass__ = PoolMeta


class NereidUser:
    "Nereid User"
    __name__ = 'nereid.user'

    activities = fields.One2Many(
        'nereid.activity', 'actor', 'Activities'
    )

    def _json(self):
        """
        Serialize the actor alone and return a dictionary. This is separated
        so that other modules can easily modify the behavior independent of
        this modules.
        """
        return {
            "url": None,
            "objectType": self.__name__,
            "id": self.id,
            "displayName": self.display_name,
        }


class Activity(ModelSQL, ModelView):
    '''
    Nereid user activity

    The model stores activities (verb) performed by nereid users (actor). The
    field names and data structure is inspired by the activity stream json
    specification 1.0 http://activitystrea.ms/specs/json/1.0/
    '''
    __name__ = 'nereid.activity'

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

    @classmethod
    def __setup__(cls):
        super(Activity, cls).__setup__()
        cls._order = [('create_date', 'DESC')]

    def get_score(self, name):
        """
        Returns an integer score which could be used for sorting the activities
        by external system like caches, which may not be able to sort on the
        date

        This score is based on the create date of the activity.

        :param name: name of field.

        :return: Integer Score.
        """
        return int(self.create_date.strftime('%s'))

    @classmethod
    def models_get(cls):
        '''
        Return valid models where activity stream could have valid objects
        and targets.
        '''
        ActivityAllowedModel = Pool().get('nereid.activity.allowed_model')

        activity_allowed_models = ActivityAllowedModel.search([])
        res = [(None, '')]
        for allowed_model in activity_allowed_models:
            res.append((allowed_model.model.model, allowed_model.name))
        return res

    def serialize(self):
        '''
        Return a JSON Seralizable dictionary that could be stored in a
        cache and sent by XHR.

        If additional information needs to be passed with the serialized data,
        a subclass could get the returned dictionary and inject properties
        anywhere in the dictionary (to be JSON object). This is respected by
        the JSON Activity Streams 1.0 spec.
        '''
        if not self.search([('id', '=', self.id)], count=True):
            return None

        if not self.object_:
            # When the object_ which caused the activity is no more
            # the value will be False
            return None

        response_json = {
            "published": self.create_date.isoformat(),
            "actor": self.actor._json(),
            "verb": self.verb,
        }

        try:
            self.object_.rec_name
        except UserError:
            # The record may not exist anymore which results in
            # a read error
            return None
        else:
            response_json["object"] = self.object_._json()

        if self.target:
            try:
                self.target.rec_name
            except UserError:
                # The record may not exist anymore which results in
                # a read error
                return None
            else:
                response_json["target"] = self.target._json()

        return response_json

    @classmethod
    def get_activity_stream_domain(cls):
        '''
        Returns the domain to get activity stream
        '''
        return []

    @classmethod
    def stream(cls):
        '''
        Return JSON Serialized Activity Stream to XHR.
        As defined by the activity stream json specification 1.0
        http://activitystrea.ms/specs/json/1.0/
        '''
        offset = request.args.get('offset', 0, int)
        limit = request.args.get('limit', 100, int)

        activities = cls.search(
            cls.get_activity_stream_domain(),
            limit=limit, offset=offset,
        )

        items = filter(
            None, map(lambda activity: activity.serialize(), activities)
        )

        return jsonify({
            'totalItems': len(items),
            'items': items,
        })


class ActivityAllowedModel(ModelSQL, ModelView):
    '''
    Nereid activity allowed model

    The model stores name (name) and model (ir.model) as list of allowed model
    in activty.
    '''
    __name__ = 'nereid.activity.allowed_model'

    name = fields.Char("Name", required=True, select=True)
    model = fields.Many2One('ir.model', 'Model', required=True, select=True)

    @classmethod
    def __setup__(cls):
        super(ActivityAllowedModel, cls).__setup__()
        cls._sql_constraints += [
            ('unique_model', 'UNIQUE(model)',
                'Name is already used.'),
            ('unique_name', 'UNIQUE(name)',
                'Model is already used.'),
        ]
